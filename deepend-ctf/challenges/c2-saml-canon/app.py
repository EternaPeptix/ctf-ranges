#!/usr/bin/env python3
"""
c1/CVE-2026-117691 — Keycloak SAML HTTP-Redirect binding percent-encoding
parser differential.

The signature check keys on the LITERAL parameter name `SAMLResponse`, but the
message processor percent-DECODES parameter names and reads whatever decodes to
`SAMLResponse`. So `%53AMLResponse=<forged>` carries an unsigned assertion the
signature layer never looks at, yet the processor happily consumes it.
(Novel: name-canonicalization differential in the redirect binding, not XSW.)

Isolated training range — do not deploy.
"""
import base64, hmac, hashlib, re, urllib.parse
from flask import Flask, request, jsonify

FLAG = "0DAY{saml_r3d1r3ct_p3rc3nt_nam3_c4n0n_d1ff}"
IDP_SIGNING_SECRET = b"idp-redirect-signing-key-not-yours"   # attacker doesn't have it
ADMIN = "admin@deepend.local"
app = Flask(__name__)


def raw_pairs():
    """(name, value) pairs exactly as sent — names NOT decoded."""
    qs = request.environ.get("QUERY_STRING", "")
    out = []
    for p in qs.split("&"):
        if not p:
            continue
        k, _, v = p.partition("=")
        out.append((k, v))
    return out


def verify_redirect_signature(pairs):
    """RFC-style: signature is over `SAMLResponse=..&SigAlg=..` (literal names)."""
    d = {k: v for k, v in pairs}
    signed = "SAMLResponse=%s&SigAlg=%s" % (d.get("SAMLResponse", ""), d.get("SigAlg", ""))
    want = hmac.new(IDP_SIGNING_SECRET, signed.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(want, d.get("Signature", ""))


@app.get("/")
def home():
    return jsonify(service="Keycloak SAML SP",
                   acs="/saml/acs?SAMLResponse=<b64>&SigAlg=...&Signature=...",
                   note="admin is " + ADMIN)


@app.get("/saml/acs")
def acs():
    pairs = raw_pairs()
    literal = {k: v for k, v in pairs}

    # --- signature layer: only engages for the LITERAL name "SAMLResponse" ---
    if "SAMLResponse" in literal:
        if not verify_redirect_signature(pairs):
            return jsonify(error="invalid redirect signature"), 403

    # --- processing layer: percent-DECODES names, then reads SAMLResponse ----
    decoded = {}
    for k, v in pairs:
        decoded[urllib.parse.unquote(k)] = v
    resp = decoded.get("SAMLResponse")
    if not resp:
        return jsonify(error="no SAMLResponse"), 400
    try:
        xml = base64.b64decode(urllib.parse.unquote(resp)).decode("utf-8", "replace")
    except Exception as e:
        return jsonify(error="bad SAMLResponse: %s" % e), 400

    m = re.search(r"<(?:\w+:)?NameID[^>]*>([^<]+)</(?:\w+:)?NameID>", xml)
    nameid = m.group(1).strip() if m else None
    if nameid == ADMIN:
        return jsonify(login="ok", nameid=nameid, flag=FLAG)
    return jsonify(login="ok", nameid=nameid, note="not an admin assertion")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, threaded=True)
