"""Shared helpers for VitaChain widgets (pure stdlib)."""
import hmac, hashlib, json, base64


def b64u(b):
    if isinstance(b, str):
        b = b.encode()
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def ub64u(s):
    s += "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s.encode())


def hmac_sha256(key, msg):
    if isinstance(key, str):
        key = key.encode()
    if isinstance(msg, str):
        msg = msg.encode()
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def jdump(obj):
    # canonical, compact JSON (stable signing payloads)
    return json.dumps(obj, separators=(",", ":"), sort_keys=True)
