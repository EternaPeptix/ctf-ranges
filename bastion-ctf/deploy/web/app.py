#!/usr/bin/env python3
"""
Bastion  —  bastion.example  ("Military-grade security.")

A portal that looks airtight. Each flag sits behind ONE non-obvious insight —
brutal to spot black-box, a one-liner once you know it:

  1. zero-width characters hide a flag in the page text        (invisible stego)
  2. the "reserved name" block uses lower() but the admin check
     uses NFKC — `ᴬdmin` slips past the block yet normalizes to admin
  3. the session cookie is AES-ECB; shuffle ciphertext blocks to
     forge role=admin  (cut-and-paste, Cryptopals 13)
  4. request signatures are md5(secret || data); length-extend one
     to append admin=1  (length extension)
  5. the preview allowlist uses re.search (no anchors), so any URL
     *containing* 'bastion.internal' is fetched -> SSRF to the
     localhost-only flag

Isolated training range — do not deploy.
"""
import os, re, json, hashlib, unicodedata, base64, urllib.request
from flask import Flask, request, jsonify, Response
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

app = Flask(__name__)

FLAGS = {
    1: "BAS{z3r0_w1dth_chars_h1d1ng_1n_pl41n_s1ght}",
    2: "BAS{nfkc_n0rm4liz4t10n_h0m0glyph_4dm1n}",
    3: "BAS{ecb_cut_4nd_p4st3_bl0ck_shuffl3}",
    4: "BAS{md5_l3ngth_3xt3ns10n_f0rg3d_s1gn4tur3}",
    5: "BAS{un4nch0r3d_r3g3x_ssrf_t0_l0c4lh0st}",
}

# ---- crypto material (random per boot; never exposed) ----------------------
ECB_KEY = os.urandom(16)
SIG_KEY = b"c0rrect-h0rse-16"           # 16 bytes; length is the only "secret" for C4
RESERVED = {"admin", "root"}

def pkcs7(b, n=16): p = n - (len(b) % n); return b + bytes([p]) * p
def unpkcs7(b):
    if not b: return b
    p = b[-1]
    return b[:-p] if 1 <= p <= 16 and b[-p:] == bytes([p]) * p else b
def ecb_enc(pt):
    e = Cipher(algorithms.AES(ECB_KEY), modes.ECB()).encryptor()
    return e.update(pkcs7(pt)) + e.finalize()
def ecb_dec(ct):
    d = Cipher(algorithms.AES(ECB_KEY), modes.ECB()).decryptor()
    return unpkcs7(d.update(ct) + d.finalize())


# ---- C1: zero-width stego (built into the landing page) -------------------
def zw_encode(s: str) -> str:
    bits = "".join(f"{byte:08b}" for byte in s.encode())
    return "".join("​" if b == "0" else "‌" for b in bits)

LANDING = """<!doctype html><html><head><meta charset="utf-8">
<title>Bastion — military-grade security</title>
<style>body{{font:16px/1.7 -apple-system,Segoe UI,Arial;max-width:680px;margin:48px auto;padding:0 20px;color:#111}}
h1{{color:#0b3d2e}} .seal{{color:#0b3d2e;font-weight:700}} .muted{{color:#8a94a6}}</style></head>
<body>
<h1>\U0001f6e1️ Bastion</h1>
<p>Enterprise document custody with <span class="seal">military-grade{zw} end-to-end</span> protection.</p>
<p>Every request is signed. Every session is encrypted. Every byte is accounted for.
   There is nothing to see here, and we are very proud of that.</p>
<p class="muted">API: POST /api/register · GET /vault · GET /api/report · GET /api/preview</p>
</body></html>"""


@app.route("/")
def home():
    # the flag is woven into the page as zero-width characters
    return Response(LANDING.format(zw=zw_encode(FLAGS[1])), mimetype="text/html")


# ---- C2: NFKC-vs-lower() reserved-name bypass -----------------------------
@app.post("/api/register")
def register():
    data = request.get_json(force=True, silent=True) or {}
    name = data.get("name")
    if not isinstance(name, str) or not name:
        return jsonify(error="name required"), 400
    # block reserved names (case-insensitive)...
    if name.lower() in RESERVED:
        return jsonify(error="that name is reserved"), 403
    # ...but decide privilege with NFKC normalisation (the mismatch)
    role = "admin" if unicodedata.normalize("NFKC", name).lower() in RESERVED else "user"
    token = base64.b64encode(ecb_enc(f"name={name}&role=user".encode())).decode()
    out = {"name": name, "role": role, "token": token,
           "note": "your session token encrypts name=<you>&role=user"}
    if role == "admin":
        out["flag"] = FLAGS[2]
        out["note"] = "your name normalises (NFKC) to a reserved admin name."
    return jsonify(out)


# ---- C3: AES-ECB cut-and-paste --------------------------------------------
def read_token():
    return (request.cookies.get("token") or request.args.get("token")
            or request.headers.get("X-Token") or "")

@app.get("/vault")
def vault():
    tok = read_token()
    try:
        pt = ecb_dec(base64.b64decode(tok)).decode("latin1")
    except Exception:
        return jsonify(error="no valid session token"), 401
    fields = dict(kv.split("=", 1) for kv in pt.split("&") if "=" in kv)
    if fields.get("role") == "admin":
        return jsonify(role="admin", flag=FLAGS[3], note="session decrypts to role=admin")
    return jsonify(role=fields.get("role", "?"), note="vault is admins only")


# ---- C4: MD5 length extension ---------------------------------------------
def sig_for(data: bytes) -> str:
    return hashlib.md5(SIG_KEY + data).hexdigest()

@app.get("/api/report")
def report():
    data_hex = request.args.get("data")
    sig = request.args.get("sig")
    if not data_hex or not sig:
        # hand the player a valid (data, sig) pair and the scheme
        sample = b"user=guest&report=q3"
        return jsonify(scheme="sig = md5(secret || data), secret length unknown",
                       example={"data": sample.hex(), "sig": sig_for(sample)},
                       note="GET /api/report?data=<hex>&sig=<hex>; admin reports need admin=1")
    try:
        data = bytes.fromhex(data_hex)
    except ValueError:
        return jsonify(error="data must be hex"), 400
    if sig_for(data) != sig:
        return jsonify(error="bad signature"), 403
    if b"admin=1" in data:
        return jsonify(flag=FLAGS[4], note="valid signature over a message you never got signed")
    return jsonify(ok=True, note="valid signature, but not an admin report")


# ---- C5: unanchored allowlist regex -> SSRF -------------------------------
@app.get("/api/preview")
def preview():
    url = request.args.get("url")
    if not url:
        return jsonify(note="preview a resource from our CDN",
                       example="/api/preview?url=https://cdn.bastion.internal/logo.png",
                       diagnostics="internal metrics are proxied from http://127.0.0.1/_internal/*")
    if not re.search(r"bastion\.internal", url):          # <-- unanchored: substring anywhere
        return jsonify(error="url must be within bastion.internal"), 403
    try:
        with urllib.request.urlopen(url, timeout=2) as r:
            body = r.read(2048).decode("latin1")
    except Exception as e:
        return jsonify(error=f"fetch failed: {e}"), 502
    return Response(body, mimetype="text/plain")

@app.get("/_internal/flag")
def internal_flag():
    if request.remote_addr != "127.0.0.1":
        return jsonify(error="internal only (localhost)"), 403
    return Response(FLAGS[5] + "\n", mimetype="text/plain")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, threaded=True)
