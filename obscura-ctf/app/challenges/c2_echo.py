"""c2 — echo : "Passwordless proof of identity."

Log in by proving knowledge of the admin's discrete log x (where Y = g^x) with
a Schnorr identification protocol, made non-interactive by Fiat-Shamir:

    prover  : commitment  t = g^v
    challenge (server): e = H(Y || nonce)        # <-- the BUG
    prover  : response   z = v + e*x
    verify  : g^z == t * Y^e

Flaw (original): the Fiat-Shamir challenge omits the commitment `t`.  A sound
transform must bind `t` (e = H(Y || t || nonce)).  Because `e` here does not
depend on `t`, an attacker who knows only the PUBLIC key Y can pick `z` first
and *back-solve* the commitment:

        choose z, compute  t = g^z * Y^(-e)

Then  g^z == t * Y^e  holds by construction — a valid proof with no witness.
"""
import secrets
from flask import Flask, request, jsonify
from common import P, Q, G, H

FLAG = "FLAG{echo_fiat_shamir_must_bind_the_commitment_a7d20e}"

_x = secrets.randbelow(Q - 2) + 1            # admin secret (never leaves server)
_Y = pow(G, _x, P)                           # admin public key
_pending = set()                             # issued, unused nonces

app = Flask(__name__)


@app.get("/")
def home():
    return jsonify(
        widget="echo — passwordless Schnorr identity proofs",
        group={"p": hex(P), "q": hex(Q), "g": G},
        admin_public_key=hex(_Y),
        protocol="non-interactive Schnorr; e = H(Y || nonce); verify g^z == t*Y^e",
        endpoints={
            "GET  /challenge": "returns a fresh nonce to prove against",
            "POST /login {nonce,t,z}": "accepts a proof of knowledge of the admin key; prints the flag",
        },
    )


@app.get("/challenge")
def challenge():
    n = secrets.token_hex(16)
    _pending.add(n)
    return jsonify(nonce=n)


@app.post("/login")
def login():
    j = request.get_json(silent=True) or {}
    n = j.get("nonce", "")

    def _int(v):
        if isinstance(v, str):
            return int(v, 16)
        return int(v)

    try:
        t = _int(j.get("t", 0)) % P
        z = _int(j.get("z", 0)) % Q
    except (TypeError, ValueError):
        return jsonify(error="t,z must be integers or hex strings"), 400
    if n not in _pending:
        return jsonify(error="unknown or already-used nonce; GET /challenge first"), 400
    _pending.discard(n)
    e = H(_Y, n) % Q                         # BUG: t is not in the hash
    lhs = pow(G, z, P)
    rhs = (t * pow(_Y, e, P)) % P
    if lhs == rhs:
        return jsonify(ok=True, flag=FLAG)
    return jsonify(ok=False, error="proof rejected"), 401
