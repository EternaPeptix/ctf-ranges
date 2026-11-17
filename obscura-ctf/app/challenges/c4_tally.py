"""c4 — tally : "Sealed envelopes."

A secrets vault encrypts each "envelope" with a one-time keystream derived from
a master key and the envelope's label:

        keystream(label) = SHA256(master || len(label) || counter) ...
        ciphertext       = plaintext XOR keystream

The admin envelope (label "admin") holds the flag.

Flaw (original): the key-derivation mixes in only `len(label)`, not the label
itself.  Every label of the SAME LENGTH shares one keystream.  Seal a
chosen plaintext under any 5-character label ("admin" is 5) and you recover
that keystream exactly, then XOR it against the admin ciphertext.
"""
import os, hashlib, struct
from flask import Flask, request, jsonify

FLAG = "FLAG{tally_keystream_keyed_only_by_label_length_d48a06}"
_MASTER = os.urandom(32)
ADMIN_LABEL = "admin"

app = Flask(__name__)


def _keystream(label, n):
    L = len(label).to_bytes(4, "big")                # only the LENGTH is used
    out = b""
    i = 0
    while len(out) < n:
        out += hashlib.sha256(_MASTER + L + struct.pack(">I", i)).digest()
        i += 1
    return out[:n]


def _xor(a, b):
    return bytes(x ^ y for x, y in zip(a, b))


_ADMIN_CT = _xor(FLAG.encode(), _keystream(ADMIN_LABEL, len(FLAG)))


@app.get("/")
def home():
    return jsonify(
        widget="tally — sealed one-time envelopes",
        kdf="keystream = SHA256(master || len(label) || counter); ct = pt XOR keystream",
        endpoints={
            "GET /seal?label=<s>&data=<hex>": "seal chosen data under a label; returns ciphertext hex",
            "GET /admin": "the admin envelope (label 'admin'); returns its ciphertext hex",
        },
    )


@app.get("/seal")
def seal():
    label = request.args.get("label", "")
    data_hex = request.args.get("data", "")
    try:
        data = bytes.fromhex(data_hex)
    except ValueError:
        return jsonify(error="data must be hex"), 400
    if label == ADMIN_LABEL:
        return jsonify(error="the label 'admin' is reserved"), 403
    ct = _xor(data, _keystream(label, len(data)))
    return jsonify(label=label, ciphertext=ct.hex())


@app.get("/admin")
def admin():
    return jsonify(label=ADMIN_LABEL, ciphertext=_ADMIN_CT.hex(),
                   note="sealed under label 'admin'")
