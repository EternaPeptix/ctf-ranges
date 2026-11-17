"""c08 — CVE-2026-53548 : Termix IDOR. The host-password endpoint returns any
host's stored SSH secret by numeric id with no ownership check."""
from flask import Flask, request, jsonify

FLAG = "FLAG{termix_id0r_ssh_passw0rd_by_id}"
HOSTS = {
    1: {"owner": "admin", "label": "prod-bastion", "password": FLAG, "sudoPassword": FLAG},
    2: {"owner": "you",   "label": "my-vps",       "password": "hunter2", "sudoPassword": "toor"},
}
app = Flask(__name__)

@app.get("/")
def home():
    return jsonify(service="Termix", hint="your host is id 2: /host/db/host/2/password?field=password")

@app.get("/host/db/host/<int:hid>/password")
def host_password(hid):
    field = request.args.get("field", "password")
    h = HOSTS.get(hid)
    if not h:
        return jsonify(error="no such host"), 404
    if field not in ("password", "sudoPassword"):
        return jsonify(error="bad field"), 400
    # BUG: no check that this host belongs to the caller
    return jsonify(id=hid, owner=h["owner"], label=h["label"], **{field: h[field]})
