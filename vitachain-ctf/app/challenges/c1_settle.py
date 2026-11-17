"""c1 — settle : "Pay with crypto, instantly confirmed."

Based on CVE-2026-9189 (Contact Form 7 PayPal/Stripe add-on) and the classic
callback-forgery class (H1 #682617, Starbucks). VitaChain's checkout confirms
orders from a signed payment-provider webhook.

The webhook does everything that *looks* right:
  * verifies the provider HMAC signature over the raw body   (origin is genuine)
  * requires payment_status == "paid"   (not merely "complete" — delayed methods)
  * requires the currency to match the order
...and then marks orders[payload.invoice] as paid.

Flaw (real): it NEVER checks that the amount paid covers the order total — the
invoice is bound to the payment the attacker initiated, not to the money. Make a
genuine $1.00 payment but set its `invoice` to a $5,000 VIP order; the provider
signs that, and the webhook settles the VIP order for a dollar.
"""
import json, secrets, time
from flask import Flask, request, jsonify
from common import hmac_sha256, jdump

FLAG = "FLAG{settle_signed_webhook_never_bound_the_amount_4c1a7e}"

# Shared secret between VitaChain and the payment provider. Server-side only —
# the attacker cannot forge signatures; they must obtain a genuine one.
_PROVIDER_SECRET = secrets.token_hex(32)

PRODUCTS = {
    "whey":  {"name": "Grass-Fed Whey (2kg)",      "usd": 59.0},
    "omega": {"name": "Arctic Omega-3 (120ct)",    "usd": 34.0},
    "vip":   {"name": "VIP Lifetime Membership",   "usd": 5000.0},
}
ORDERS = {}   # id -> {sku, usd, currency, status}

app = Flask(__name__)


def _new_order(sku):
    oid = "ord_" + secrets.token_hex(5)
    ORDERS[oid] = {"sku": sku, "usd": PRODUCTS[sku]["usd"], "currency": "USD", "status": "pending"}
    return oid


@app.get("/")
def home():
    return jsonify(
        shop="VitaChain checkout",
        products=PRODUCTS,
        flow="POST /order/create -> POST /pay/provider -> POST /webhook/payment -> GET /order/<id>",
        endpoints={
            "POST /order/create {sku}": "create an order, returns {order_id, usd}",
            "POST /pay/provider {invoice,amount,currency}": "make a payment; the provider returns a SIGNED confirmation",
            "POST /webhook/payment {payload,signature}": "provider -> VitaChain settlement callback",
            "GET  /order/<id>": "order status (reveals the flag once a VIP order is paid)",
        },
    )


@app.post("/order/create")
def order_create():
    j = request.get_json(silent=True) or {}
    sku = j.get("sku", "")
    if sku not in PRODUCTS:
        return jsonify(error="unknown sku", products=list(PRODUCTS)), 400
    oid = _new_order(sku)
    return jsonify(order_id=oid, sku=sku, usd=ORDERS[oid]["usd"], currency="USD")


@app.post("/pay/provider")
def pay_provider():
    """Models the external crypto payment provider. You really pay `amount`, but
    — exactly as a real PayPal/gateway custom-field — YOU choose the `invoice`."""
    j = request.get_json(silent=True) or {}
    try:
        amount = float(j.get("amount", 0))
    except (TypeError, ValueError):
        return jsonify(error="amount must be a number"), 400
    invoice = str(j.get("invoice", ""))
    currency = str(j.get("currency", "USD"))
    if amount <= 0:
        return jsonify(error="you must actually pay something (amount > 0)"), 402
    payload = jdump({
        "invoice": invoice,
        "amount": round(amount, 2),
        "currency": currency,
        "payment_status": "paid",
        "txn_id": "tx_" + secrets.token_hex(8),
        "ts": int(time.time()),
    })
    return jsonify(payload=payload, signature=hmac_sha256(_PROVIDER_SECRET, payload))


@app.post("/webhook/payment")
def webhook_payment():
    j = request.get_json(silent=True) or {}
    payload = j.get("payload", "")
    signature = j.get("signature", "")
    # 1) origin: the provider HMAC must verify over the exact bytes
    if not isinstance(payload, str) or hmac_sha256(_PROVIDER_SECRET, payload) != signature:
        return jsonify(error="invalid provider signature"), 401
    try:
        ev = json.loads(payload)
    except ValueError:
        return jsonify(error="unparseable payload"), 400
    oid = str(ev.get("invoice", ""))
    order = ORDERS.get(oid)
    if not order:
        return jsonify(error="unknown invoice"), 404
    # 2) not merely "complete" — must be settled
    if ev.get("payment_status") != "paid":
        return jsonify(error="payment not settled"), 402
    # 3) currency must match the order
    if ev.get("currency") != order["currency"]:
        return jsonify(error="currency mismatch"), 402
    # 4) settle.  BUG: the amount is never compared to order["usd"].
    order["status"] = "paid"
    return jsonify(ok=True, invoice=oid, status="paid")


@app.get("/order/<oid>")
def order_get(oid):
    order = ORDERS.get(oid)
    if not order:
        return jsonify(error="unknown order"), 404
    out = {"order_id": oid, "sku": order["sku"], "usd": order["usd"],
           "currency": order["currency"], "status": order["status"]}
    if order["status"] == "paid" and order["sku"] == "vip":
        out["membership"] = "ACTIVE"
        out["flag"] = FLAG
    return jsonify(out)
