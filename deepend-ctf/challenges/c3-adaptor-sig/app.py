#!/usr/bin/env python3
"""
c3/CVE-2026-55174 — UltrafastSecp256k1 ECDSA adaptor-signature forgery.

An ECDSA adaptor pre-signature is (K, K_Y, r, s_hat). Correct verification must
prove K_Y is bound to the adaptor point Y (a DLEQ between (G,K) and (Y,K_Y)) and
that r = x(K_Y). The vulnerable verifier checks the ECDSA-style relation and
r = x(K_Y), but NEVER binds K_Y to Y — so r is effectively free. That lets anyone
forge a pre-signature on any message with only the public key: pick any point as
K_Y (giving r), set s_hat = 1, and choose K = H(m)*G + r*P so the relation holds.

Isolated training range — do not deploy.
"""
import hashlib, secrets
from flask import Flask, request, jsonify
from ecdsa import SECP256k1
from ecdsa.ellipticcurve import Point

G = SECP256k1.generator
N = SECP256k1.order
CURVE = SECP256k1.curve

x = secrets.randbelow(N - 1) + 1          # signer's secret key (attacker never learns it)
P = x * G
y = secrets.randbelow(N - 1) + 1          # adaptor witness
Y = y * G
TARGET = "transfer:all-funds->attacker"   # a pre-signature on THIS is the win
FLAG = "0DAY{3cdsa_4dapt0r_pr3s1g_unb0und_t0_T}"

app = Flask(__name__)

def Hm(m): return int.from_bytes(hashlib.sha256(m.encode()).digest(), "big") % N
def point(j): return Point(CURVE, int(j[0]), int(j[1]), N)


@app.get("/params")
def params():
    return jsonify(curve="secp256k1", n=str(N),
                   P=[str(P.x()), str(P.y())], Y=[str(Y.x()), str(Y.y())],
                   target=TARGET,
                   note="POST /presign/verify {m,K,K_Y,r,s_hat}; a verifying pre-signature on the target wins")


@app.post("/presign/verify")
def presign_verify():
    b = request.get_json(force=True, silent=True) or {}
    try:
        m = b["m"]; K = point(b["K"]); K_Y = point(b["K_Y"])
        r = int(b["r"]) % N; s_hat = int(b["s_hat"]) % N
    except Exception as e:
        return jsonify(error="bad pre-signature: %s" % e), 400
    if not (1 <= r < N and 1 <= s_hat < N):
        return jsonify(error="r,s_hat out of range"), 400
    # ECDSA-style relation with K as the nonce point
    lhs = s_hat * K
    rhs = (Hm(m) % N) * G + r * P
    if lhs != rhs:
        return jsonify(valid=False, reason="relation s_hat*K == H(m)*G + r*P failed")
    # binds r to K_Y ... but never checks K_Y against the adaptor point Y (the flaw)
    if r != K_Y.x() % N:
        return jsonify(valid=False, reason="r != x(K_Y)")
    if m == TARGET:
        return jsonify(valid=True, flag=FLAG, note="forged a pre-signature you could never legitimately make")
    return jsonify(valid=True, note="valid pre-signature (non-target message)")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, threaded=True)
