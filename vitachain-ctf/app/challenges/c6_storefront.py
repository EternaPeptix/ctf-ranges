"""c6 — storefront : "One storefront API, every receipt a click away."

Combines two real-world bug classes into one black-box GraphQL endpoint:

  * GraphQL BOLA via opaque global node IDs — HackerOne #2207248 (Shopify).
    The API hands out "global IDs" (base64 of gid://vitachain/Invoice/<n>) and
    leans on them as if they were unguessable capabilities. One field (`invoice`)
    checks that the node belongs to your shop; a sibling field (`receipt`)
    resolves the SAME opaque id but forgets the ownership check — textbook Broken
    Object-Level Authorization. Decode a gid, re-encode any integer, and
    `receipt` reads a row that belongs to another tenant.

  * Alias batching past a rate limiter — HackerOne #2166697.
    The limiter throttles HTTP *requests* (8 per rolling 10s), but a single
    GraphQL document can carry hundreds of aliased fields. The engine counts the
    request exactly once and then executes every alias, so one POST does the work
    of a thousand serial probes.

Defences that look reassuring but do not actually help: introspection is
disabled (the schema is a black box), the vulnerable field is only ONE of the
two that accept an Invoice id, the ids are opaque base64, and a serial
brute-force of the admin's invoice id (somewhere in 0..999) gets throttled after
8 tries. The intended solve is a SINGLE aliased request that sweeps every id in
one rate-limit tick and lifts the admin's receipt body — which carries the flag.
"""
import base64, random, re, threading, time
from flask import Flask, request, jsonify

FLAG = "FLAG{storefront_opaque_ids_batched_past_the_limit_88c0de}"

SESSION_SHOP = "s_7"          # the attacker's low-privilege tenant (session shop)


# ---- opaque global node ids ------------------------------------------------
def _gid(n):
    """Encode an integer invoice id as an opaque base64 global node id."""
    return base64.b64encode(f"gid://vitachain/Invoice/{n}".encode()).decode()


def _ungid(gid):
    """Recover the integer n from an opaque Invoice gid, or None if it is junk."""
    try:
        raw = base64.b64decode(gid.encode()).decode()
    except Exception:
        return None
    m = re.fullmatch(r"gid://vitachain/Invoice/(\d+)", raw)
    return int(m.group(1)) if m else None


# ---- data model : invoices belong to shops ---------------------------------
# The admin invoice id is fixed ONCE, at import time, somewhere in 0..999.
_ADMIN_ID = random.randint(0, 999)
while _ADMIN_ID == 7:                      # keep it distinct from the attacker's row
    _ADMIN_ID = random.randint(0, 999)

INVOICES = {
    # The attacker owns invoice #7 in their own shop.
    7: {
        "id": 7,
        "shop": SESSION_SHOP,
        "total": 42.0,
        "body": "Order #7 — 2x Grass-Fed Whey, 1x steel shaker. Thanks for shopping VitaChain!",
    },
    # The admin/ops invoice — different tenant, and its body carries the flag.
    _ADMIN_ID: {
        "id": _ADMIN_ID,
        "shop": "s_ops",
        "total": 9999.0,
        "body": f"INTERNAL ops reconciliation — settlement key {FLAG}",
    },
}


# ---- request rate limiter (counts HTTP requests, NOT operations) -----------
_RATE_LOCK = threading.Lock()
_REQ_WINDOW = []              # timestamps of recent /graphql HTTP requests
_RATE_MAX = 8                 # allowed requests ...
_RATE_WINDOW_S = 10          # ... per rolling window (seconds)


def _rate_ok():
    """Tick ONCE per HTTP request, independent of how many aliased operations the
    body carries. Returns True while still within the allowance."""
    now = time.time()
    with _RATE_LOCK:
        cutoff = now - _RATE_WINDOW_S
        _REQ_WINDOW[:] = [t for t in _REQ_WINDOW if t >= cutoff]
        _REQ_WINDOW.append(now)            # one HTTP request == one tick
        return len(_REQ_WINDOW) <= _RATE_MAX


# ---- a hand-rolled, deliberately loose GraphQL-ish parser ------------------
# <alias>: <field>(id: "<gid>") { ... }   — field is receipt or invoice.
_FIELD_RE = re.compile(
    r'(?:(?P<alias>[A-Za-z_]\w*)\s*:\s*)?'
    r'\b(?P<field>receipt|invoice)\s*\(\s*id\s*:\s*"(?P<gid>[^"]*)"\s*\)'
)
# myInvoice { id gid body }   — no arguments; returns your own row + its gid.
_MYINV_RE = re.compile(r'(?:(?P<alias>[A-Za-z_]\w*)\s*:\s*)?\bmyInvoice\b')


def _run_query(query):
    """Resolve a (loosely parsed) query string into a GraphQL-style envelope."""
    # Introspection is disabled — the schema is a black box.
    if "__schema" in query or "__type" in query:
        return {"errors": [{"message": "introspection disabled"}]}

    data = {}
    matched = False

    # myInvoice — your own invoice, including its opaque gid (teaches the scheme).
    mm = _MYINV_RE.search(query)
    if mm:
        matched = True
        key = mm.group("alias") or "myInvoice"
        inv = INVOICES[7]
        data[key] = {"id": inv["id"], "gid": _gid(inv["id"]), "body": inv["body"]}

    # receipt / invoice fields — any number, aliased or not.
    for fm in _FIELD_RE.finditer(query):
        matched = True
        field = fm.group("field")
        key = fm.group("alias") or field
        n = _ungid(fm.group("gid"))
        inv = INVOICES.get(n) if n is not None else None

        if field == "invoice":
            # SAFE path: enforce object-level authorization on the shop.
            if inv is None or inv["shop"] != SESSION_SHOP:
                return {"errors": [{"message": "forbidden"}]}
            data[key] = {"total": inv["total"]}
        else:
            # receipt — BOLA: resolves ANY id with no ownership check at all.
            data[key] = {"body": inv["body"] if inv else None}

    if not matched:
        return {"errors": [{"message": "no operation in query"}]}
    return {"data": data}


app = Flask(__name__)


@app.get("/")
def home():
    return jsonify(
        shop="VitaChain storefront GraphQL",
        session_shop=SESSION_SHOP,
        endpoint="POST /graphql {query}",
        policy={
            "introspection": "disabled",
            "rate_limit": f"{_RATE_MAX} requests / {_RATE_WINDOW_S}s (per HTTP request)",
        },
        operations={
            "myInvoice { id gid body }": "your own invoice, including its opaque gid",
            'invoice(id: "<gid>") { total }': "an invoice total — ENFORCES shop ownership",
            'receipt(id: "<gid>") { body }': "a receipt body, resolved by opaque id",
        },
    )


@app.post("/graphql")
def graphql():
    # Count the HTTP request first — a single POST is one tick no matter how many
    # aliased operations it carries.
    if not _rate_ok():
        return jsonify(errors=[{"message": "rate limited"}]), 429
    j = request.get_json(silent=True) or {}
    query = j.get("query", "")
    if not isinstance(query, str):
        return jsonify(errors=[{"message": "query must be a string"}]), 400
    return jsonify(_run_query(query))
