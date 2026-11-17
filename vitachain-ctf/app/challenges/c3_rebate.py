"""c3 — rebate : "Redeem your VitaBucks gift card."

Based on H1 #759247 (Reverb — redeem a gift card many times via a race) and the
TOCTOU redemption class (#1717650 Stripe promo-limit, #157996 Instacart coupon).

A $25 gift card is single-use. Redeeming credits your store balance and marks the
card used. VIP costs $100 — four times the card — so one honest redemption is not
enough.

Flaw (real): redemption is check-then-mark with a real settlement window in
between and NO atomicity on the "used" flag. Fire many redemptions concurrently
and they all pass the `used?` check before any of them sets it — one $25 card
credits you again and again. (A balance lock keeps the math exact; the bug is
purely the unsynchronized used-flag.)
"""
import threading, time
from flask import Flask, request, jsonify

FLAG = "FLAG{rebate_check_then_credit_is_not_atomic_2e7d64}"
VIP_PRICE = 100
CARD = {"code": "VITA-GIFT-25", "value": 25, "used": False}
STATE = {"balance": 0, "vip": False}
_balance_lock = threading.Lock()              # keeps credits from clobbering each other

app = Flask(__name__)


@app.get("/")
def home():
    return jsonify(
        shop="VitaChain rewards",
        gift_card=CARD["code"],
        card_value=CARD["value"],
        vip_price=VIP_PRICE,
        endpoints={
            "POST /redeem {code}": "redeem the gift card -> +balance (single use)",
            "GET  /me": "your balance",
            "POST /buy {sku}": "spend balance; 'vip' reveals the flag",
        },
    )


@app.post("/redeem")
def redeem():
    j = request.get_json(silent=True) or {}
    if j.get("code") != CARD["code"]:
        return jsonify(error="unknown gift card"), 404
    if CARD["used"]:                           # CHECK
        return jsonify(error="gift card already redeemed"), 409
    time.sleep(0.15)                           # settlement window (DB round-trip) -> TOCTOU
    with _balance_lock:
        STATE["balance"] += CARD["value"]      # ACT (balance math is correct)
    CARD["used"] = True                        # MARK (too late — others already passed CHECK)
    return jsonify(credited=CARD["value"], balance=STATE["balance"])


@app.get("/me")
def me():
    return jsonify(balance=STATE["balance"], vip=STATE["vip"])


@app.post("/buy")
def buy():
    j = request.get_json(silent=True) or {}
    if j.get("sku") != "vip":
        return jsonify(error="only 'vip' is interesting"), 400
    with _balance_lock:
        if STATE["balance"] < VIP_PRICE:
            return jsonify(error="insufficient balance", need=VIP_PRICE, have=STATE["balance"]), 402
        # Reveal the flag, then reset the round so the organizer self-check is
        # repeatable (a fresh card + zero balance for the next run).
        STATE["balance"] = 0
        CARD["used"] = False
    return jsonify(ok=True, membership="ACTIVE", flag=FLAG)
