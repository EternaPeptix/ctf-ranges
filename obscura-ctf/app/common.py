"""Shared math for Obscura's crypto widgets.

A single Schnorr group over a 2048-bit MODP *safe* prime (RFC 3526 group 14):
q = (p-1)/2 is prime, and g = 4 generates the order-q subgroup of quadratic
residues.  Exponents live mod q.  Pure stdlib — no external crypto.
"""
import hashlib

# RFC 3526 2048-bit MODP safe prime.
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
    """Length-prefixed SHA-256 over a mixed list of ints / bytes / str -> int."""
    h = hashlib.sha256()
    for x in parts:
        if isinstance(x, int):
            x = x.to_bytes((x.bit_length() + 7) // 8 or 1, "big")
        elif isinstance(x, str):
            x = x.encode()
        h.update(len(x).to_bytes(4, "big"))
        h.update(x)
    return int.from_bytes(h.digest(), "big")


def inv(a, m):
    return pow(a % m, -1, m)
