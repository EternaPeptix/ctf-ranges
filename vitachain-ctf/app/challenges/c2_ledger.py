"""c2 — ledger : "On-chain deposits, credited in real time."

Based on H1 #300748 (Coinbase — Ethereum account balance manipulation).
VitaChain watches the chain and credits store balance from the *internal
value-transfer traces* of a deposit transaction.

The mock chain is faithful in the one way that matters: a NON-reverting tx must
be covered by the sender's balance (you cannot mint money). But a tx can also
*revert* — its state changes roll back, yet `debug_traceTransaction` still lists
the attempted internal transfers.

Flaw (real): the deposit indexer sums the trace transfers to your deposit
address and credits them WITHOUT checking the top-level receipt status. Craft a
transaction that "pays" your deposit address and then reverts: nothing actually
moves on-chain, but VitaChain credits you anyway.
"""
import secrets
from flask import Flask, request, jsonify

FLAG = "FLAG{ledger_credited_a_reverted_transaction_b9f330}"
VIP_PRICE = 5000

DEPOSIT_ADDR = "vc_dep_" + secrets.token_hex(6)
_CHAIN = {}                                   # txhash -> {traces, receipt_status}
_SCANNED = set()                              # txhashes already credited
STATE = {"balance": 0.0, "vip": False}
# sender account the attacker transacts from — deliberately broke.
_ACCT_BALANCE = 0.0

app = Flask(__name__)


@app.get("/")
def home():
    return jsonify(
        shop="VitaChain on-chain deposits",
        deposit_address=DEPOSIT_ADDR,
        vip_price=VIP_PRICE,
        your_chain_balance=_ACCT_BALANCE,
        flow="POST /chain/broadcast -> POST /deposit/scan -> POST /buy",
        endpoints={
            "POST /chain/broadcast {transfers:[{to,value}], revert:bool}": "submit a tx; returns {txhash, receipt_status}",
            "POST /deposit/scan {txhash}": "index the tx and credit deposits to your balance",
            "GET  /me": "your store balance",
            "POST /buy {sku}": "spend balance; 'vip' reveals the flag",
        },
    )


@app.post("/chain/broadcast")
def broadcast():
    j = request.get_json(silent=True) or {}
    transfers = j.get("transfers", [])
    revert = bool(j.get("revert", False))
    if not isinstance(transfers, list) or not transfers:
        return jsonify(error="transfers must be a non-empty list of {to,value}"), 400
    try:
        total = sum(float(t["value"]) for t in transfers)
    except (KeyError, TypeError, ValueError):
        return jsonify(error="each transfer needs numeric 'value' and a 'to'"), 400
    # Chain rule: a SUCCESSFUL tx must be covered by the sender's balance.
    # A reverting tx applies nothing — but its attempted transfers are still traced.
    if not revert and total > _ACCT_BALANCE:
        return jsonify(error="insufficient funds for a non-reverting tx",
                       sender_balance=_ACCT_BALANCE), 400
    txhash = "0x" + secrets.token_hex(32)
    _CHAIN[txhash] = {
        "traces": [{"to": str(t["to"]), "value": float(t["value"])} for t in transfers],
        "receipt_status": "reverted" if revert else "success",
    }
    return jsonify(txhash=txhash, receipt_status=_CHAIN[txhash]["receipt_status"])


@app.post("/deposit/scan")
def scan():
    j = request.get_json(silent=True) or {}
    txhash = str(j.get("txhash", ""))
    tx = _CHAIN.get(txhash)
    if not tx:
        return jsonify(error="unknown txhash"), 404
    if txhash in _SCANNED:
        return jsonify(error="already credited", balance=STATE["balance"]), 409
    credited = 0.0
    for tr in tx["traces"]:                    # BUG: never checks tx["receipt_status"]
        if tr["to"] == DEPOSIT_ADDR and tr["value"] > 0:
            credited += tr["value"]
    if credited <= 0:
        return jsonify(error="no deposits to your address in this tx"), 400
    _SCANNED.add(txhash)
    STATE["balance"] += credited
    return jsonify(credited=credited, balance=STATE["balance"],
                   receipt_status=tx["receipt_status"])


@app.get("/me")
def me():
    return jsonify(balance=STATE["balance"], vip=STATE["vip"])


@app.post("/buy")
def buy():
    j = request.get_json(silent=True) or {}
    if j.get("sku") != "vip":
        return jsonify(error="only 'vip' is interesting"), 400
    if STATE["balance"] < VIP_PRICE:
        return jsonify(error="insufficient balance", need=VIP_PRICE, have=STATE["balance"]), 402
    STATE["balance"] -= VIP_PRICE
    STATE["vip"] = True
    return jsonify(ok=True, membership="ACTIVE", flag=FLAG)
