"""
old_api_server.py – lightweight aiohttp wrapper around the trusted process_card()
from Autoshopify (1).py.

Listens on  0.0.0.0:5000
Endpoints:
  GET /shopify?site=…&cc=CC|MM|YY|CVV&proxy=host:port:user:pass&variant=…
  GET /health

Concurrency:
  - Global asyncio.Semaphore(10)  – limits total in-flight checkouts
  - Per-domain asyncio.Semaphore(2) – prevents hammering a single store
  - Requests exceeding the global limit are rejected with HTTP 429 immediately
    so the bot can back off and retry.
"""

import asyncio
import importlib.util
import json
import logging
import os
import sys
import time
from collections import defaultdict
from urllib.parse import urlparse

from aiohttp import web

try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass

# ── logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("old_api_server")

# ── concurrency constants ─────────────────────────────────────────────────────
HOST = "0.0.0.0"
PORT = 5000
MAX_CONCURRENT_CHECKS = 10   # global in-flight limit
MAX_DOMAIN_CONCURRENT = 2    # per-domain limit
REQUEST_TIMEOUT = 45          # seconds – per checkout

# ── load process_card from Autoshopify (1).py ─────────────────────────────────
_SOURCE_FILE = os.path.join(os.path.dirname(__file__), "Autoshopify (1).py")

def _load_autoshopify():
    """Import Autoshopify (1).py as a module using importlib (handles spaces/parens)."""
    spec = importlib.util.spec_from_file_location("autoshopify_legacy", _SOURCE_FILE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot find {_SOURCE_FILE!r}")
    mod = importlib.util.module_from_spec(spec)
    # Suppress Flask's own startup noise during import
    sys.modules["autoshopify_legacy"] = mod
    spec.loader.exec_module(mod)
    return mod

try:
    _autoshopify = _load_autoshopify()
    process_card = _autoshopify.process_card
    parse_cc_string = _autoshopify.parse_cc_string
    extract_clean_response = _autoshopify.extract_clean_response
    logger.info("Loaded process_card from %s", _SOURCE_FILE)
except Exception as exc:
    logger.critical("Failed to load Autoshopify module: %s", exc)
    sys.exit(1)

# ── shared state ──────────────────────────────────────────────────────────────
_global_semaphore: asyncio.Semaphore
_domain_semaphores: dict  # domain → asyncio.Semaphore
_active_count: int = 0

def _get_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower() or url
    except Exception:
        return url

# ── request handler ───────────────────────────────────────────────────────────

async def handle_shopify(request: web.Request) -> web.Response:
    global _active_count

    site = request.rel_url.query.get("site", "").strip()
    cc_string = request.rel_url.query.get("cc", "").strip()
    proxy_str = request.rel_url.query.get("proxy", "").strip() or None
    variant_id = request.rel_url.query.get("variant", "").strip() or None

    if not site:
        return web.json_response(
            {"Status": False, "Response": "Missing 'site' parameter"}, status=400
        )
    if not cc_string:
        return web.json_response(
            {"Status": False, "Response": "Missing 'cc' parameter"}, status=400
        )

    try:
        cc_parts = parse_cc_string(cc_string)
    except ValueError as exc:
        return web.json_response(
            {"Status": False, "Response": f"Invalid CC format: {exc}"}, status=400
        )

    cc  = cc_parts["cc"]
    mes = cc_parts["mes"]
    ano = cc_parts["ano"]
    cvv = cc_parts["cvv"]

    domain = _get_domain(site)

    # ── global overload check (non-blocking) ────────────────────────────────
    if _global_semaphore.locked() and _active_count >= MAX_CONCURRENT_CHECKS:
        return web.json_response(
            {"Status": False, "Response": "Server overloaded – try again shortly",
             "Gateway": "SHOPIFY", "Price": 0.0, "currency": "USD", "cc": cc_string},
            status=429,
        )

    start = time.monotonic()

    async def _do_checkout():
        global _active_count
        async with _global_semaphore:
            dom_sem = _domain_semaphores[domain]
            async with dom_sem:
                _active_count += 1
                try:
                    return await process_card(cc, mes, ano, cvv, site, variant_id, proxy_str)
                finally:
                    _active_count -= 1

    try:
        result = await asyncio.wait_for(_do_checkout(), timeout=REQUEST_TIMEOUT)
    except asyncio.TimeoutError:
        elapsed = time.monotonic() - start
        logger.warning("[timeout] %s | %.1fs", domain, elapsed)
        return web.json_response(
            {"Status": False, "Response": "Timeout", "Gateway": "SHOPIFY",
             "Price": 0.0, "currency": "USD", "cc": cc_string},
            status=504,
        )
    except Exception as exc:
        logger.exception("[error] %s | %s", domain, exc)
        return web.json_response(
            {"Status": False, "Response": f"Error: {str(exc)[:120]}",
             "Gateway": "SHOPIFY", "Price": 0.0, "currency": "USD", "cc": cc_string},
            status=500,
        )

    elapsed = time.monotonic() - start
    success, message, gateway, price, currency = result
    clean = extract_clean_response(message)

    try:
        price_f = float(price) if str(price).replace(".", "", 1).replace("-", "", 1).isdigit() else 0.0
    except (TypeError, ValueError):
        price_f = 0.0

    logger.info("[done] %s | %.2fs | gw=%s | status=%s | resp=%s",
                domain, elapsed, gateway, success, clean)

    return web.json_response({
        "Status": success,
        "Response": clean,
        "Gateway": gateway or "SHOPIFY",
        "Price": price_f,
        "currency": currency or "USD",
        "cc": cc_string,
    })


async def handle_health(request: web.Request) -> web.Response:
    return web.json_response({
        "status": "ok",
        "active": _active_count,
        "max": MAX_CONCURRENT_CHECKS,
        "domain_semaphores": len(_domain_semaphores),
    })


# ── application factory ───────────────────────────────────────────────────────

async def on_startup(app):
    global _global_semaphore, _domain_semaphores
    _global_semaphore = asyncio.Semaphore(MAX_CONCURRENT_CHECKS)
    _domain_semaphores = defaultdict(lambda: asyncio.Semaphore(MAX_DOMAIN_CONCURRENT))
    logger.info("Server ready – MAX_CONCURRENT_CHECKS=%d, MAX_DOMAIN_CONCURRENT=%d",
                MAX_CONCURRENT_CHECKS, MAX_DOMAIN_CONCURRENT)


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/shopify", handle_shopify)
    app.router.add_get("/health", handle_health)
    app.on_startup.append(on_startup)
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host=HOST, port=PORT, access_log=None)
