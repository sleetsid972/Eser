# ══════════════════════════════════════════════════════════════════
#  Gunicorn Configuration — Optimised for 4 vCPU / 31 GB RAM Azure VPS
#
#  Launch:
#    gunicorn -c gunicorn.conf.py autoshopify:app
# ══════════════════════════════════════════════════════════════════

import multiprocessing

# ── Workers ─────────────────────────────────────────────────────
# 3 workers: API gets ~2 CPU cores, bot gets ~1.5 cores, OS keeps rest.
# Do NOT use 2×CPU+1 (= 9) here — the bot process also runs on this machine.
workers = 3
threads = 4                  # per-worker thread pool (gthread worker class)
worker_class = "gthread"     # sync Flask + thread pool; no monkey-patching

# ── Binding ─────────────────────────────────────────────────────
bind = "127.0.0.1:5000"      # localhost only; put nginx/haproxy in front if needed

# ── Timeouts ────────────────────────────────────────────────────
timeout = 60                 # Shopify checkout can take up to 30s; give headroom
graceful_timeout = 30        # on SIGTERM, wait up to 30s for in-flight requests
keepalive = 15               # keep HTTP connection open 15s (bot reuses connection)

# ── Memory/leak protection ──────────────────────────────────────
max_requests = 2000          # recycle worker after N requests (prevents slow leaks)
max_requests_jitter = 200    # randomise recycling so all workers don't restart at once

# ── RAM disk for worker heartbeat files ─────────────────────────
# Avoids Azure SSD I/O on heartbeat writes; /dev/shm is RAM-backed tmpfs
worker_tmp_dir = "/dev/shm"

# ── Logging ─────────────────────────────────────────────────────
accesslog = "-"              # stdout → systemd journal
errorlog  = "-"
loglevel  = "info"
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s %(D)sµs'

# ── Performance ─────────────────────────────────────────────────
preload_app = False          # False: each worker has its own event loop (safe for our background thread)
forwarded_allow_ips = "127.0.0.1"
