"""c1 — reverb : "Reproducible signatures."

Obscura's signing appliance uses textbook Schnorr over a 2048-bit safe-prime
group, and ships a convenience feature: *deterministic, reproducible nonces*.
Per key it draws one secret `seed`; the nonce for the i-th signature is

        k_i = seed * r^i   (mod q)

where `r` is a FIXED, PUBLICLY PUBLISHED ratio ("so you can regenerate any
signature offline, given only the seed").  The counter `i` is returned with
every signature.

Flaw (original): structured nonces are *linearly dependent*.  Each signature
is one linear equation  s_i = k_i + e_i*d = seed*r^i + e_i*d  in the two
unknowns (seed, d).  TWO signatures => a 2x2 system mod q => full key recovery.
Then anyone can forge the one signature the oracle refuses to make.
"""
import secrets
from flask import Flask, request, jsonify
from common import P, Q, G, H

FLAG = "FLAG{reverb_deterministic_nonces_are_linear_8f3c91}"
ADMIN_MSG = "grant-admin"

_d = secrets.randbelow(Q - 2) + 1            # secret signing key
_Y = pow(G, _d, P)                           # public key
_seed = secrets.randbelow(Q - 2) + 1         # secret per-key nonce seed
R = H("reverb/ratio/v1") % Q                 # PUBLIC advertised ratio r
_ctr = [0]

app = Flask(__name__)


def _sign(msg):
    i = _ctr[0]; _ctr[0] += 1
    k = (_seed * pow(R, i, Q)) % Q
    Rc = pow(G, k, P)
    e = H(Rc, msg) % Q
    s = (k + e * _d) % Q
    return i, e, s


def _verify(msg, e, s):
    e %= Q; s %= Q
    Rv = (pow(G, s, P) * pow(_Y, (Q - e) % Q, P)) % P
    return (H(Rv, msg) % Q) == e


@app.get("/")
def home():
    return jsonify(
        widget="reverb — reproducible Schnorr signatures",
        group={"p": hex(P), "q": hex(Q), "g": G},
        public_key=hex(_Y),
        nonce_scheme="k_i = seed * r^i mod q  (deterministic, reproducible)",
        public_ratio_r=hex(R),
        endpoints={
            "GET  /sign?msg=...": "sign any message except the admin command; returns {i,e,s}",
            "POST /admin {msg,e,s}": "runs the signed command; '%s' prints the flag" % ADMIN_MSG,
        },
    )


@app.get("/sign")
def sign():
    msg = request.args.get("msg", "")
    if msg == ADMIN_MSG:
        return jsonify(error="the appliance will not sign the privileged command"), 403
    i, e, s = _sign(msg)
    return jsonify(i=i, e=hex(e), s=hex(s))


@app.post("/admin")
def admin():
    j = request.get_json(silent=True) or {}
    msg = j.get("msg", "")
    try:
        e = int(j.get("e", "0"), 16) if isinstance(j.get("e"), str) else int(j.get("e", 0))
        s = int(j.get("s", "0"), 16) if isinstance(j.get("s"), str) else int(j.get("s", 0))
    except (TypeError, ValueError):
        return jsonify(error="e,s must be integers or hex strings"), 400
    if msg != ADMIN_MSG:
        return jsonify(error="unknown command"), 400
    if _verify(msg, e, s):
        return jsonify(ok=True, flag=FLAG)
    return jsonify(ok=False, error="signature does not verify"), 401
