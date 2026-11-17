#!/usr/bin/env python3
"""
Stage-7 solver: recover the Keyhaven signer's ECDSA private key from biased
nonces via the Hidden Number Problem, then sign the root manifest.

Collect m signatures (r_i, s_i, z_i) whose nonces satisfy 0 <= k_i < 2^(256-B):
    k_i = s_i^-1 (z_i + r_i d)  =  a_i + t_i d   (mod n),   a_i=s^-1 z, t_i=s^-1 r
Build the HNP lattice (scaled by n to stay integer), LLL-reduce, read d out of
the short vector, sign the challenge, POST it to /forge.

Pure-Python LLL so the range needs no exotic deps (only `ecdsa`).
Usage: hnp_solve.py <base_url>     e.g. http://localhost:80  or  http://app..../gw/signer
"""
import sys, json, hashlib, secrets, urllib.request
from fractions import Fraction
from ecdsa import NIST256p
from ecdsa.numbertheory import inverse_mod
from ecdsa.ellipticcurve import Point

G = NIST256p.generator
N = NIST256p.order
CURVE = NIST256p.curve


# ---- compact fraction-based LLL -------------------------------------------
def lll(B, delta=Fraction(99, 100)):
    B = [list(map(int, row)) for row in B]
    n, m = len(B), len(B[0])
    Bs = [None] * n
    mu = [[Fraction(0)] * n for _ in range(n)]
    nrm = [Fraction(0)] * n

    def gso():
        for i in range(n):
            vi = [Fraction(x) for x in B[i]]
            bs = vi[:]
            for j in range(i):
                sij = sum(Fraction(B[i][k]) * Bs[j][k] for k in range(m))
                mu[i][j] = sij / nrm[j]
                bs = [bs[k] - mu[i][j] * Bs[j][k] for k in range(m)]
            Bs[i] = bs
            nrm[i] = sum(x * x for x in bs)

    gso()
    k = 1
    while k < n:
        for j in range(k - 1, -1, -1):
            if abs(mu[k][j]) > Fraction(1, 2):
                q = round(mu[k][j])
                B[k] = [B[k][t] - q * B[j][t] for t in range(m)]
                gso()
        if nrm[k] >= (delta - mu[k][k - 1] ** 2) * nrm[k - 1]:
            k += 1
        else:
            B[k], B[k - 1] = B[k - 1], B[k]
            gso()
            k = max(k - 1, 1)
    return B


def solve(base, nsigs=8, bias=64):
    def getj(path):
        return json.load(urllib.request.urlopen(base + path, timeout=15))
    def postj(path, obj):
        req = urllib.request.Request(base + path, data=json.dumps(obj).encode(),
                                     headers={"Content-Type": "application/json"})
        return urllib.request.urlopen(req, timeout=15).read().decode()

    pub = getj("/pubkey")
    Q = Point(CURVE, pub["Qx"], pub["Qy"], N)
    challenge = pub["challenge"]
    K = 1 << (256 - bias)

    # collect biased signatures
    t, a = [], []
    for i in range(nsigs):
        sig = postj("/sign", {"message": f"build-manifest-{i}-{secrets.token_hex(4)}"})
        sig = json.loads(sig)
        si = inverse_mod(sig["s"], N)
        t.append((si * sig["r"]) % N)
        a.append((si * sig["z"]) % N)

    # HNP lattice (scaled by n): dim nsigs+2
    m = nsigs
    B = [[0] * (m + 2) for _ in range(m + 2)]
    for i in range(m):
        B[i][i] = N * N
    for i in range(m):
        B[m][i] = N * t[i]
    B[m][m] = K
    for i in range(m):
        B[m + 1][i] = N * a[i]
    B[m + 1][m + 1] = K * N

    red = lll(B)

    def check(d):
        d %= N
        if d == 0:
            return False
        return (d * G) == Q

    d = None
    for row in red:
        cands = []
        if row[m + 1] != 0 and row[m] % K == 0:
            cands += [row[m] // K, -row[m] // K]
        # also derive from a per-sig coordinate: w[i] = n*k_i
        if row[0] % N == 0:
            k0 = (row[0] // N) % N
            cands.append(((k0 - a[0]) * inverse_mod(t[0], N)) % N)
            cands.append(((-k0 - a[0]) * inverse_mod(t[0], N)) % N)
        for c in cands:
            if check(c):
                d = c % N
                break
        if d is not None:
            break
    if d is None:
        return None, "key recovery failed"

    # sign the challenge with the recovered key and submit
    z = int.from_bytes(hashlib.sha256(challenge.encode()).digest(), "big") % N
    while True:
        k = secrets.randbelow(N - 1) + 1
        r = (k * G).x() % N
        if r == 0:
            continue
        s = (inverse_mod(k, N) * (z + r * d)) % N
        if s:
            break
    out = postj("/forge", {"r": r, "s": s})
    return d, out


if __name__ == "__main__":
    base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:80"
    d, out = solve(base)
    if d is None:
        print("FAILED:", out); sys.exit(1)
    print("recovered d =", hex(d))
    print(out)
