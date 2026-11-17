"""c3 — warden : "Signed download links."

A gateway hands out HMAC-signed links so a client can fetch files under the
public area only.  The signer authorizes a request by checking the path prefix,
then signs the path.  The fetcher verifies the HMAC, then resolves the file.

    GET /token?path=/public/<...>   ->  if path.startswith('/public/'): HMAC(path)
    GET /fetch?path=...&token=...    ->  verify HMAC(path); then open the file

Flaw (original): the authorization and the signature both operate on the RAW,
still-percent-encoded path, but the fetcher URL-DECODES and path-normalizes
before opening.  `authorize/sign -> decode -> normalize -> open` is the wrong
order.  A path like `/public/%2e%2e/admin/flag.txt` literally *starts with*
`/public/`, so it is authorized and signed verbatim; only later does it decode
to `/public/../admin/flag.txt` and normalize to `/admin/flag.txt`.
"""
import os, hmac, hashlib
from urllib.parse import unquote
from flask import Flask, request, jsonify, Response

FLAG = "FLAG{warden_authorize_then_normalize_is_backwards_5b1e74}"
_KEY = os.urandom(32)
BASE = os.environ.get("DATA_DIR", "/data")

app = Flask(__name__)


def _setup():
    os.makedirs(BASE + "/public", exist_ok=True)
    os.makedirs(BASE + "/admin", exist_ok=True)
    with open(BASE + "/public/manual.txt", "w") as f:
        f.write("Obscura Warden — public manual.\nServe files from /public/ only.\n")
    with open(BASE + "/admin/flag.txt", "w") as f:
        f.write(FLAG + "\n")


_setup()


def _sign(path):
    return hmac.new(_KEY, path.encode(), hashlib.sha256).hexdigest()


@app.get("/")
def home():
    return jsonify(
        widget="warden — HMAC-signed download links",
        policy="tokens are only issued for paths under /public/",
        endpoints={
            "GET /token?path=/public/...": "returns an HMAC token for an authorized path",
            "GET /fetch?path=...&token=...": "verifies the token and returns the file",
        },
        example="/token?path=/public/manual.txt",
    )


@app.get("/token")
def token():
    path = request.args.get("path", "")
    if not path.startswith("/public/"):           # authorize on the RAW path
        return jsonify(error="only /public/ paths may be signed"), 403
    return jsonify(path=path, token=_sign(path))   # ...and sign the RAW path


@app.get("/fetch")
def fetch():
    path = request.args.get("path", "")
    tok = request.args.get("token", "")
    if not hmac.compare_digest(_sign(path), tok):
        return jsonify(error="bad or missing token"), 401
    # decode + normalize happen only now — AFTER authorization & signing
    decoded = unquote(path)
    full = os.path.normpath(os.path.join(BASE, decoded.lstrip("/")))
    if not full.startswith(BASE):                  # stay inside the data root
        return jsonify(error="resolved outside data root"), 400
    if not os.path.isfile(full):
        return jsonify(error="not found", resolved=full), 404
    with open(full, "rb") as f:
        return Response(f.read(), mimetype="text/plain")
