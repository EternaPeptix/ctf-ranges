"""c5 — passport : "Stateless JWT single-sign-on."

Based on H1 #1210502 (Jitsi/8x8 — RS256->HS256 key confusion) with a twist that
makes it genuinely hard: the public key is NOT published (no JWKS endpoint).

The verifier accepts BOTH RS256 (RSA, verified against the server's public key)
and HS256 (verified as HMAC-SHA256 with the PEM public key as the secret) — the
classic algorithm-confusion bug. To forge an HS256 admin token you need the exact
public-key bytes... which the server never hands out.

But the `/token` oracle issues RS256-signed tokens, and the public exponent is
small (e = 3). From two signatures you can recover the modulus:
    s = EM^d mod N   =>   s^e ≡ EM (mod N)   =>   N | (s_i^e − EM_i)
    N = gcd(s_1^e − EM_1, s_2^e − EM_2, …)   (strip small factors)
Rebuild the SubjectPublicKeyInfo PEM from (N, e), HMAC an `{"role":"admin"}`
token with it under alg HS256, and VitaChain's SSO waves you through.
"""
import json, hmac, hashlib, secrets, base64, random, math
from flask import Flask, request, jsonify
from common import b64u, ub64u

FLAG = "FLAG{passport_rsa_pubkey_from_sigs_then_hs256_d15ea5}"
E = 3

app = Flask(__name__)

# ---------------------------------------------------------------- RSA (stdlib)
def _is_prime(n, k=40):
    if n < 2:
        return False
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if n % p == 0:
            return n == p
    d, r = n - 1, 0
    while d % 2 == 0:
        d //= 2; r += 1
    for _ in range(k):
        a = random.randrange(2, n - 1)
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(r - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def _gen_prime(bits):
    while True:
        p = random.getrandbits(bits) | (1 << (bits - 1)) | 1
        if p % 3 == 2 and _is_prime(p):     # p % 3 == 2  => gcd(e=3, p-1) == 1
            return p


_p, _q = _gen_prime(512), _gen_prime(512)
while _p == _q:
    _q = _gen_prime(512)
N = _p * _q
_lam = (_p - 1) * (_q - 1) // math.gcd(_p - 1, _q - 1)   # Carmichael lambda
D = pow(E, -1, _lam)
K = (N.bit_length() + 7) // 8                            # modulus byte length


# ------------------------------------------------- PKCS#1 v1.5 (SHA-256) EMSA
_SHA256_DIGESTINFO = bytes.fromhex("3031300d060960864801650304020105000420")


def _emsa_pkcs1(msg, k):
    h = hashlib.sha256(msg).digest()
    t = _SHA256_DIGESTINFO + h
    ps = b"\xff" * (k - len(t) - 3)
    return b"\x00\x01" + ps + b"\x00" + t


def _i2b(x, n):
    return x.to_bytes(n, "big")


def _b2i(b):
    return int.from_bytes(b, "big")


# --------------------------------------------------------- DER SubjectPublicKeyInfo
def _der_len(n):
    if n < 0x80:
        return bytes([n])
    b = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(b)]) + b


def _der_int(x):
    b = x.to_bytes((x.bit_length() + 7) // 8 or 1, "big")
    if b[0] & 0x80:
        b = b"\x00" + b
    return b"\x02" + _der_len(len(b)) + b


def _der_seq(*parts):
    body = b"".join(parts)
    return b"\x30" + _der_len(len(body)) + body


def _der_bitstring(data):
    return b"\x03" + _der_len(len(data) + 1) + b"\x00" + data


_OID_RSA = b"\x06\x09\x2a\x86\x48\x86\xf7\x0d\x01\x01\x01"   # rsaEncryption
_ASN_NULL = b"\x05\x00"


def public_pem():
    """Canonical OpenSSL-style SubjectPublicKeyInfo PEM for (N, E)."""
    rsa_pub = _der_seq(_der_int(N), _der_int(E))
    algid = _der_seq(_OID_RSA, _ASN_NULL)
    spki = _der_seq(algid, _der_bitstring(rsa_pub))
    b64 = base64.b64encode(spki).decode()
    lines = "\n".join(b64[i:i + 64] for i in range(0, len(b64), 64))
    return f"-----BEGIN PUBLIC KEY-----\n{lines}\n-----END PUBLIC KEY-----\n"


_PEM = public_pem().encode()


# ------------------------------------------------------------------- JWT core
def _issue(payload):
    header = b64u(json.dumps({"alg": "RS256", "typ": "JWT"}, separators=(",", ":")))
    body = b64u(json.dumps(payload, separators=(",", ":")))
    signing_input = f"{header}.{body}".encode()
    em = _b2i(_emsa_pkcs1(signing_input, K))
    s = pow(em, D, N)
    return f"{header}.{body}." + b64u(_i2b(s, K))


def _verify(token):
    try:
        h_b64, p_b64, sig_b64 = token.split(".")
    except ValueError:
        return None
    header = json.loads(ub64u(h_b64))
    signing_input = f"{h_b64}.{p_b64}".encode()
    alg = header.get("alg")
    sig = ub64u(sig_b64)
    if alg == "RS256":
        s = _b2i(sig)
        em = pow(s, E, N)
        if em != _b2i(_emsa_pkcs1(signing_input, K)):
            return None
    elif alg == "HS256":
        # BUG: symmetric verification using the PEM public key as the secret.
        expect = hmac.new(_PEM, signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(expect, sig):
            return None
    else:
        return None
    try:
        return json.loads(ub64u(p_b64))
    except ValueError:
        return None


@app.get("/")
def home():
    return jsonify(
        service="VitaChain SSO",
        jwt={"alg": "RS256", "exponent": E, "note": "public key is not published"},
        endpoints={
            "GET  /token": "issue an RS256 session token (role=user)",
            "GET  /admin": "Authorization: Bearer <jwt>; role=admin reveals the flag",
        },
    )


@app.get("/token")
def token():
    payload = {"sub": "user_" + secrets.token_hex(4), "role": "user",
               "iat": secrets.randbelow(1 << 31)}
    return jsonify(token=_issue(payload))


@app.get("/admin")
def admin():
    auth = request.headers.get("Authorization", "")
    tok = auth[7:] if auth.startswith("Bearer ") else request.args.get("token", "")
    claims = _verify(tok)
    if not claims:
        return jsonify(error="invalid token"), 401
    if claims.get("role") != "admin":
        return jsonify(error="not an admin", role=claims.get("role")), 403
    return jsonify(ok=True, flag=FLAG)
