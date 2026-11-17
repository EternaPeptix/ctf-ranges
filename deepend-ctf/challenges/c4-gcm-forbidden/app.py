#!/usr/bin/env python3
"""
c4/CVE-2026-81020 — AES-GCM nonce reuse ("forbidden attack", Joux).

This "secure channel" encrypts every message with the SAME key AND nonce (the
wolfEngine bug: the explicit nonce is fixed per write-key and never incremented).
Two ciphertexts under one (key, nonce) let an attacker recover the GHASH
authentication key H over GF(2^128) and then forge a valid tag for any message
of the same length -> authenticate the privileged command without the key.

Isolated training range — do not deploy.
"""
import os
from flask import Flask, request, jsonify
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

FLAG = "0DAY{aes_gcm_f0rb1dd3n_4ttack_r3c0v3r_H}"
KEY = os.urandom(16)
NONCE = os.urandom(12)                  # fixed + reused for every message (the bug)
TARGET = b"GIVE-ME-ADMIN!!!"            # 16 bytes; the command you must authenticate
app = AESGCM(KEY)
flask_app = Flask(__name__)


@flask_app.get("/")
def home():
    return jsonify(service="GCM secure channel",
                   nonce=NONCE.hex(),
                   note="GET /encrypt?msg=<16 bytes> ; POST /command {ct,tag} to run a signed command",
                   target="authenticate the plaintext %r" % TARGET.decode())


@flask_app.get("/encrypt")
def encrypt():
    msg = request.args.get("msg", "").encode("latin1")
    if not msg:
        return jsonify(error="msg required"), 400
    blob = app.encrypt(NONCE, msg, b"")       # same nonce every time
    return jsonify(ct=blob[:-16].hex(), tag=blob[-16:].hex())


@flask_app.post("/command")
def command():
    b = request.get_json(force=True, silent=True) or {}
    try:
        ct = bytes.fromhex(b["ct"]); tag = bytes.fromhex(b["tag"])
    except Exception:
        return jsonify(error="hex ct,tag required"), 400
    try:
        pt = app.decrypt(NONCE, ct + tag, b"")   # verifies the forged tag
    except Exception:
        return jsonify(error="authentication failed"), 403
    if pt == TARGET:
        return jsonify(ok=True, command=pt.decode("latin1"), flag=FLAG)
    return jsonify(ok=True, command=pt.decode("latin1"), note="not the privileged command")


if __name__ == "__main__":
    flask_app.run(host="0.0.0.0", port=80, threaded=True)
