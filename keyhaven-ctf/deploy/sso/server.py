#!/usr/bin/env python3
"""
Keyhaven SSO  —  sso.corp.keyhaven.example

Two faithful, deep vulnerabilities:

 * CVE-2019-18277 (framing): this raw-socket front reads a request as chunked if
   ANY `Transfer-Encoding` header contains `chunked` (lenient/last-wins), while
   the edge only honours the FIRST TE when it is exactly `chunked` (else
   Content-Length). That disagreement lets an attacker smuggle a request in the
   body to reach `/internal/*`, bypassing the edge ACL.  -> stage 1

 * CVE-2018-0489 (SAML XML signature wrapping): the SAML assertion consumer
   validates the XML signature by following the Signature's Reference URI to the
   element it protects (crypto-correct), but then resolves the authenticated
   subject from the FIRST <Assertion> in the document by position. An attacker
   wraps a validly-signed guest assertion with an unsigned admin assertion placed
   first: the signature still verifies (over the untouched guest assertion) while
   the SP trusts the attacker's admin identity.  -> stage 2

Isolated training range — do not deploy.
"""
import os, socket, threading, base64, hashlib, hmac, copy, urllib.parse
from lxml import etree
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes

FLAG1 = "KH{t3_cl_d3sync_smuggl3d_past_th3_edg3_acl}"
FLAG2 = "KH{saml_xsw_s1gn3d_0n3_assert10n_tru5t3d_an0th3r}"

# corp gateway session token (shared with the edge; issued on SAML-admin login)
CORP_TOKEN = hmac.new(os.getenv("KH_CORP_SECRET", "k3yh4v3n-c0rp-s3cr3t-2026").encode(),
                      b"corp-admin", hashlib.sha256).hexdigest()

NS = {"samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
      "saml":  "urn:oasis:names:tc:SAML:2.0:assertion",
      "ds":    "http://www.w3.org/2000/09/xmldsig#"}

# ---- IdP signing key (ephemeral; the XSW attack never needs it) -------------
IDP_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
IDP_PUB = IDP_KEY.public_key()


def c14n(el):
    return etree.tostring(el, method="c14n", exclusive=True, with_comments=False)


def build_signed_response(nameid, role):
    """Build a Response>Assertion for `nameid`/`role`, enveloped-signed over the
    assertion (Reference URI=#<assertion id>)."""
    R = "urn:oasis:names:tc:SAML:2.0:protocol"
    A = "urn:oasis:names:tc:SAML:2.0:assertion"
    D = "http://www.w3.org/2000/09/xmldsig#"
    resp = etree.Element(f"{{{R}}}Response", nsmap={"samlp": R, "saml": A})
    resp.set("ID", "_resp_0001")
    assertion = etree.SubElement(resp, f"{{{A}}}Assertion")
    aid = "_assert_guest_7f3c"
    assertion.set("ID", aid)
    subj = etree.SubElement(assertion, f"{{{A}}}Subject")
    nid = etree.SubElement(subj, f"{{{A}}}NameID")
    nid.text = nameid
    atts = etree.SubElement(assertion, f"{{{A}}}AttributeStatement")
    att = etree.SubElement(atts, f"{{{A}}}Attribute")
    att.set("Name", "role")
    av = etree.SubElement(att, f"{{{A}}}AttributeValue")
    av.text = role

    # enveloped digest over the assertion (no Signature present yet)
    digest = hashlib.sha256(c14n(assertion)).digest()

    sig = etree.SubElement(assertion, f"{{{D}}}Signature")
    si = etree.SubElement(sig, f"{{{D}}}SignedInfo")
    etree.SubElement(si, f"{{{D}}}CanonicalizationMethod").set(
        "Algorithm", "http://www.w3.org/2001/10/xml-exc-c14n#")
    etree.SubElement(si, f"{{{D}}}SignatureMethod").set(
        "Algorithm", "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256")
    ref = etree.SubElement(si, f"{{{D}}}Reference")
    ref.set("URI", "#" + aid)
    transforms = etree.SubElement(ref, f"{{{D}}}Transforms")
    etree.SubElement(transforms, f"{{{D}}}Transform").set(
        "Algorithm", "http://www.w3.org/2000/09/xmldsig#enveloped-signature")
    etree.SubElement(ref, f"{{{D}}}DigestMethod").set(
        "Algorithm", "http://www.w3.org/2001/04/xmlenc#sha256")
    etree.SubElement(ref, f"{{{D}}}DigestValue").text = base64.b64encode(digest).decode()

    sigval = IDP_KEY.sign(c14n(si), padding.PKCS1v15(), hashes.SHA256())
    etree.SubElement(sig, f"{{{D}}}SignatureValue").text = base64.b64encode(sigval).decode()
    return etree.tostring(resp)


def find_by_id(doc, idv):
    for el in doc.iter():
        if el.get("ID") == idv:
            return el
    return None


def validate_response(xml_bytes):
    """Verify the XML signature by Reference-ID (correct), then resolve the
    subject from the FIRST assertion by position (the CVE-2018-0489 flaw)."""
    try:
        doc = etree.fromstring(xml_bytes)
    except Exception as e:
        return None, f"parse error: {e}"
    sig = doc.find(".//ds:Signature", NS)
    if sig is None:
        return None, "no signature"
    ref = sig.find(".//ds:Reference", NS)
    uri = (ref.get("URI") or "").lstrip("#") if ref is not None else ""
    signed = find_by_id(doc, uri)
    if signed is None:
        return None, "reference target not found"
    # enveloped: digest the referenced element with its Signature(s) removed
    el = copy.deepcopy(signed)
    for s in el.findall(".//ds:Signature", NS):
        s.getparent().remove(s)
    digest = base64.b64encode(hashlib.sha256(c14n(el)).digest()).decode()
    dv = (sig.find(".//ds:DigestValue", NS).text or "").strip()
    if digest != dv:
        return None, "digest mismatch (signed content altered)"
    si = sig.find("./ds:SignedInfo", NS)
    try:
        sv = base64.b64decode(sig.find(".//ds:SignatureValue", NS).text)
        IDP_PUB.verify(sv, c14n(si), padding.PKCS1v15(), hashes.SHA256())
    except Exception:
        return None, "signature invalid"

    # ---- THE FLAW: identity from the FIRST assertion, not the signed one -----
    first = doc.find(".//saml:Assertion", NS)
    nid = first.find(".//saml:NameID", NS)
    nameid = nid.text if nid is not None else None
    role = None
    for attr in first.findall(".//saml:Attribute", NS):
        if attr.get("Name") == "role":
            av = attr.find("./saml:AttributeValue", NS)
            role = av.text if av is not None else None
    return {"nameid": nameid, "role": role, "signed_id": uri}, None


# ===========================================================================
#  raw-socket HTTP with the lenient (substring) chunked rule
# ===========================================================================
class Reader:
    def __init__(self, conn, pre=b""):
        self.conn = conn; self.buf = bytearray(pre); self.closed = False
    def _fill(self):
        if self.closed: return False
        try: data = self.conn.recv(4096)
        except (socket.timeout, OSError): return False
        if not data: self.closed = True; return False
        self.buf += data; return True
    def read_until(self, sep):
        while sep not in bytes(self.buf):
            if not self._fill(): break
        i = bytes(self.buf).find(sep)
        if i < 0:
            out = bytes(self.buf); self.buf = bytearray(); return out
        out = bytes(self.buf[:i + len(sep)]); del self.buf[:i + len(sep)]; return out
    def read_n(self, n):
        while len(self.buf) < n:
            if not self._fill(): break
        out = bytes(self.buf[:n]); del self.buf[:n]; return out
    def has_buffered(self): return len(self.buf) > 0
    def wait_more(self, t):
        self.conn.settimeout(t)
        try: return self._fill()
        finally:
            try: self.conn.settimeout(None)
            except OSError: pass


def parse_head(head):
    lines = head.split(b"\r\n")
    rl = lines[0].decode("latin1") if lines else ""
    parts = rl.split(" ")
    method = parts[0] if parts else "GET"
    path = parts[1] if len(parts) > 1 else "/"
    headers = []
    for ln in lines[1:]:
        if b":" in ln:
            n, _, v = ln.partition(b":")
            headers.append((n.decode("latin1").strip(), v.decode("latin1").strip()))
    return method, path, headers

def is_chunked(headers):
    return any(n.lower() == "transfer-encoding" and "chunked" in v.lower()
               for n, v in headers)

def content_length(headers):
    for n, v in headers:
        if n.lower() == "content-length" and v.strip().isdigit():
            return int(v.strip())
    return 0

def read_chunked(r):
    body = bytearray()
    while True:
        line = r.read_until(b"\r\n")
        tok = line.split(b";")[0].strip()
        try: size = int(tok, 16)
        except ValueError: break
        if size == 0:
            r.read_until(b"\r\n"); break
        body += r.read_n(size); r.read_until(b"\r\n")
    return bytes(body)


def http(status, body, ctype="text/plain; charset=utf-8", extra=""):
    if isinstance(body, str): body = body.encode()
    return (f"HTTP/1.1 {status}\r\nContent-Type: {ctype}\r\n"
            f"Content-Length: {len(body)}\r\nConnection: keep-alive\r\n{extra}\r\n"
            ).encode() + body

LANDING = """<!doctype html><title>Keyhaven SSO</title>
<body style="font:15px -apple-system,Arial;max-width:560px;margin:60px auto;color:#1b2430">
<h1 style="color:#3b5bdb">◈ Keyhaven</h1>
<p>Privacy-first single sign-on &amp; secure document vault.</p>
<form><label>Email <input name="email"></label>
<button disabled>Sign in with SAML</button></form>
<p style="color:#8a94a6;font-size:13px">app.keyhaven.example · SP metadata at /saml/metadata</p></body>"""


def route(method, path, headers, body):
    p = path.split("?", 1)[0]
    if p in ("/", "/login"):
        return http("200 OK", LANDING, "text/html; charset=utf-8")
    if p == "/saml/metadata":
        return http("200 OK", "<EntityDescriptor entityID='https://app.keyhaven.example/sp'/>",
                    "application/xml")

    if p == "/internal/bootstrap":
        return http("200 OK",
            "Keyhaven internal bootstrap (corp only)\n"
            f"ctf_flag_1={FLAG1}\n"
            "SAML assertion consumer: POST SAMLResponse (base64) to /internal/saml/acs\n"
            "A validly-signed GUEST assertion is at /internal/saml/sample .\n"
            "The SP validates the signature by its Reference URI but reads the\n"
            "subject from the first <Assertion> by position (CVE-2018-0489).\n")

    if p == "/internal/saml/sample":
        xml = build_signed_response("guest@keyhaven.example", "guest")
        return http("200 OK",
            "# validly-signed SAML Response for guest@keyhaven.example (base64)\n"
            "# wrap it: prepend an unsigned admin <Assertion> as the FIRST child\n"
            "# of <Response>, keep this signed guest assertion second, re-encode,\n"
            "# POST as SAMLResponse to /internal/saml/acs .\n"
            + base64.b64encode(xml).decode() + "\n")

    if p == "/internal/saml/acs" and method == "POST":
        form = urllib.parse.parse_qs(body.decode("latin1"))
        sr = form.get("SAMLResponse", [""])[0]
        if not sr:
            return http("400 Bad Request", "SAMLResponse required\n")
        try:
            xml = base64.b64decode(sr)
        except Exception:
            return http("400 Bad Request", "SAMLResponse not valid base64\n")
        ident, err = validate_response(xml)
        if err:
            return http("401 Unauthorized", f"SAML rejected: {err}\n")
        if ident["role"] == "admin" or (ident["nameid"] or "").startswith("admin@"):
            return http("200 OK",
                f"Signed in as {ident['nameid']} (role={ident['role']}).\n"
                f"Signature validated over assertion id={ident['signed_id']} — but you\n"
                f"are logged in as the assertion the SP read by POSITION.\n"
                f"ctf_flag_2={FLAG2}\n"
                "A corp session cookie (kh_corp) has been set. The edge now proxies the\n"
                "internal services for you at /gw/api/*, /gw/vault/*, /gw/signer/* .\n"
                "next: the internal API (/gw/api) authorises with JWTs and TRUSTS a JWK\n"
                "embedded in the token header (node-jose, CVE-2018-0114). Forge a\n"
                "service-scope token for /gw/api/admin.\n",
                extra=f"Set-Cookie: kh_corp={CORP_TOKEN}; Path=/\r\n")
        return http("200 OK",
            f"Signed in as {ident['nameid']} (role={ident['role']}). No admin access.\n")

    return http("404 Not Found", f"no route: {p}\n")


def handle_conn(conn):
    r = Reader(conn)
    try:
        while True:
            head = r.read_until(b"\r\n\r\n")
            if b"\r\n\r\n" not in head:
                break
            method, path, headers = parse_head(head.rstrip(b"\r\n"))
            if is_chunked(headers):
                body = read_chunked(r)
            else:
                cl = content_length(headers)
                body = r.read_n(cl) if cl else b""
            conn.sendall(route(method, path, headers, body))
            if not r.has_buffered():
                if not r.wait_more(0.3):
                    break
    except Exception:
        pass
    finally:
        try: conn.close()
        except Exception: pass


def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", 80)); s.listen(128)
    print("[sso] listening on :80 (lenient framing + SAML SP)", flush=True)
    while True:
        c, _ = s.accept()
        threading.Thread(target=handle_conn, args=(c,), daemon=True).start()

if __name__ == "__main__":
    main()
