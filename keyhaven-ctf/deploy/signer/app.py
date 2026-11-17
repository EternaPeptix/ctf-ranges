#!/usr/bin/env python3
"""
Keyhaven Signer  —  signer.corp.keyhaven.example  (release-manifest signing)

Two faithful crypto flaws:

 * CVE-2024-31497 (biased ECDSA nonce -> Hidden Number Problem): every signature
   uses a per-message nonce whose top bits are forced to zero (modelling PuTTY's
   P-521 nonce = truncated SHA-512). The bias leaks the private key: collect
   enough (r, s, z) tuples, build an HNP lattice, run lattice reduction, recover
   the signing key, then sign the privileged "root" manifest the service refuses
   to sign itself.  -> stage 7 (FINAL)

 * CVE-2022-21449 ("Psychic Signatures"): the manifest verifier omits the
   0 < r,s < n range check, so a blank signature (r,s)=(0,0) is accepted against
   any key.  -> bonus

(Lab note: the real PuTTY bias was 9 bits over P-521, needing ~60 signatures;
here the bias is larger over P-256 so the lattice is tractable with ~12 — the
mechanism is identical.)

Isolated training range — do not deploy.
"""
import hashlib, secrets
from flask import Flask, request, jsonify, Response
from ecdsa import SigningKey, NIST256p
from ecdsa.numbertheory import inverse_mod
from ecdsa.ellipticcurve import INFINITY

app = Flask(__name__)

FLAG7 = "KH{putty_b1as3d_n0nce_hnp_latt1ce_k3y_r3c0v3ry}"
BONUS = "KH{ecdsa_psych1c_s1gnatur3_z3r0_z3r0_4ccept3d}"

G = NIST256p.generator
N = NIST256p.order
SK = SigningKey.generate(curve=NIST256p)
D = SK.privkey.secret_multiplier               # the secret signing key
Q = SK.get_verifying_key().pubkey.point

CHALLENGE = "keyhaven:root-capability-grant:v1"  # /forge checks a sig over this
MANIFEST = "keyhaven:release-manifest"           # /verify-manifest target
BIAS = 64                                        # top 64 bits of each nonce are 0


def _z(msg: bytes) -> int:
    return int.from_bytes(hashlib.sha256(msg).digest(), "big") % N

def sign_biased(msg: bytes):
    z = _z(msg)
    while True:
        k = secrets.randbelow(1 << (256 - BIAS))   # <-- biased: high bits zero
        if k == 0:
            continue
        R = k * G
        r = R.x() % N
        if r == 0:
            continue
        s = (inverse_mod(k, N) * (z + r * D)) % N
        if s == 0:
            continue
        return r, s, z

def ecdsa_verify(z, r, s):
    if not (1 <= r < N and 1 <= s < N):     # the check CVE-2022-21449 omitted
        return False
    w = inverse_mod(s, N)
    P = (z * w % N) * G + (r * w % N) * Q
    if P == INFINITY:
        return False
    return (P.x() % N) == r


@app.route("/")
def home():
    return Response("Keyhaven signer · POST /sign {message} · GET /pubkey · "
                    "POST /forge {r,s} · POST /verify-manifest {r,s}\n", mimetype="text/plain")

@app.route("/pubkey")
def pubkey():
    return jsonify(curve="NIST256p", n=N, Qx=Q.x(), Qy=Q.y(), nonce_bias_bits=BIAS,
                   challenge=CHALLENGE,
                   note="recover the key from biased /sign nonces, sign the challenge, POST {r,s} to /forge")

@app.route("/sign", methods=["POST"])
def sign():
    msg = (request.get_json(silent=True) or {}).get("message", "")
    if not isinstance(msg, str) or not msg:
        return jsonify(error="message required"), 400
    if msg == CHALLENGE or "root" in msg:
        return jsonify(error="refusing to sign privileged/root manifests"), 403
    r, s, z = sign_biased(msg.encode())
    return jsonify(r=r, s=s, z=z)

@app.route("/forge", methods=["POST"])
def forge():
    b = request.get_json(silent=True) or {}
    try:
        r, s = int(b["r"]), int(b["s"])
    except Exception:
        return jsonify(error="integer r,s required"), 400
    if ecdsa_verify(_z(CHALLENGE.encode()), r, s):
        return Response("valid signature over the ROOT capability manifest — the master "
                        "signing key is compromised.\n"
                        f"ctf_flag_7(FINAL)={FLAG7}\n", mimetype="text/plain")
    return jsonify(valid=False), 200

@app.route("/verify-manifest", methods=["POST"])
def verify_manifest():
    b = request.get_json(silent=True) or {}
    try:
        r, s = int(b["r"]), int(b["s"])
    except Exception:
        return jsonify(error="integer r,s required"), 400
    # CVE-2022-21449: no 0<r,s<n range check -> (0,0) degenerate-verifies as valid.
    if r == 0 and s == 0:
        return Response("manifest signature accepted (no range check!).\n"
                        f"ctf_bonus={BONUS}\n", mimetype="text/plain")
    return jsonify(valid=ecdsa_verify(_z(MANIFEST.encode()), r, s)), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
