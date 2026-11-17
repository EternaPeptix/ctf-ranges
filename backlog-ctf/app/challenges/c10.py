"""c10 — CVE-2026-105986 : Kong Gateway RBAC checks the raw (un-normalized) path
while the backend decodes it -> percent-encoding bypass."""
import urllib.parse
from flask import Flask, request, jsonify, Response

FLAG = "FLAG{kong_percent_enc0d3_rbac_byp4ss}"
app = Flask(__name__)

def raw_path():
    # the path exactly as sent, before decoding
    return (request.environ.get("RAW_URI") or request.environ.get("REQUEST_URI")
            or request.full_path).split("?")[0]

@app.route("/", defaults={"_p": ""})
@app.route("/<path:_p>")
def gateway(_p):
    rp = raw_path()
    # RBAC is evaluated on the RAW path...
    if rp.lower().startswith("/admin"):
        return jsonify(error="RBAC: /admin/* requires role=admin"), 403
    # ...but the route is resolved on the DECODED path (normalization mismatch)
    decoded = urllib.parse.unquote(rp).rstrip("/")
    if decoded == "/admin/flag":
        return Response("admin route reached\n" + FLAG + "\n", mimetype="text/plain")
    if decoded in ("", "/"):
        return jsonify(service="Kong Gateway", note="GET /admin/flag is protected by RBAC")
    return jsonify(path=decoded), 404
