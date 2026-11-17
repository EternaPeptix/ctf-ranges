"""c09 — CVE-2026-54733 : Moodle local_o365 trusts the `upn` claim of a JWT with
NO signature verification -> forge any identity."""
import base64, json
from flask import Flask, request, jsonify

FLAG = "FLAG{moodle_unsigned_jwt_upn_trust}"
app = Flask(__name__)

def b64d(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))

@app.get("/")
def home():
    return jsonify(service="Moodle o365 SSO",
                   hint="/auth/oidc/sso_login?token=<jwt>; the admin is admin@bastion.local")

@app.get("/auth/oidc/sso_login")
def sso_login():
    tok = request.args.get("token", "")
    parts = tok.split(".")
    if len(parts) < 2:
        return jsonify(error="malformed token"), 400
    try:
        payload = json.loads(b64d(parts[1]))      # BUG: decoded, signature never verified
    except Exception:
        return jsonify(error="bad token"), 400
    upn = payload.get("upn", "")
    if upn == "admin@bastion.local":
        return jsonify(login="ok", upn=upn, role="siteadmin", flag=FLAG)
    return jsonify(login="ok", upn=upn, role="user")
