#!/usr/bin/env python3
"""orrery -- reference solver (standard library only, deterministic).

Sparse interpolation after Ben-Or & Tiwari, i.e. Prony's method over F_p:

  1. Spend the 32 evaluations on x_i = (2^i, 3^i, 5^i, 7^i, 11^i, 13^i), i = 0..31.
     Then v_i = f(x_i) = sum_j c_j * m_j^i, where m_j = 2^a 3^b 5^c 7^d 11^e 13^g
     is the j-th monomial of f evaluated at (2, 3, 5, 7, 11, 13).
  2. Berlekamp-Massey finds the shortest linear recurrence of (v_i); its
     characteristic polynomial is the locator prod_j (z - m_j).
  3. Cantor-Zassenhaus (fixed seed) finds the locator's roots mod p.
  4. p > 30030^20, so each root IS the integer m_j: trial division by
     2, 3, 5, 7, 11, 13 reads off the exponent vector.
  5. A Vandermonde system in the m_j gives the coefficients c_j.
"""
import json
import math
import os
import random
import sys
import time
import urllib.error
import urllib.request

BASE = os.environ.get("ORRERY_URL", "http://app").rstrip("/")
PRIMES = (2, 3, 5, 7, 11, 13)
SEED = 1729  # root finding is randomised; a fixed seed makes every run reproducible


def say(msg):
    print(msg, flush=True)


def call(path, body=None):
    """GET when body is None (retried while the service boots), else POST JSON (never retried: evals cost)."""
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, headers={"Content-Type": "application/json"})
    deadline = time.time() + 60
    while True:
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as err:
            sys.exit("[solve] %s -> HTTP %d: %s" % (path, err.code, err.read().decode(errors="replace").strip()))
        except OSError as err:
            if body is not None or time.time() > deadline:
                sys.exit("[solve] cannot reach %s%s: %s" % (BASE, path, err))
            time.sleep(0.5)


# ---- F_p[z] on ascending coefficient lists ---------------------------------------------------
def trim(a):
    while a and a[-1] == 0:
        a.pop()
    return a


def pdivmod(a, b, p):
    a, inv = a[:], pow(b[-1], -1, p)
    quo = [0] * max(len(a) - len(b) + 1, 0)
    for i in range(len(a) - len(b), -1, -1):
        quo[i] = c = a[i + len(b) - 1] * inv % p
        for j, bj in enumerate(b):
            a[i + j] = (a[i + j] - c * bj) % p
    return quo, trim(a[:len(b) - 1])


def pmulmod(a, b, m, p):
    out = [0] * (len(a) + len(b) - 1) if a and b else []
    for i, ai in enumerate(a):
        for j, bj in enumerate(b):
            out[i + j] = (out[i + j] + ai * bj) % p
    return pdivmod(out, m, p)[1]


def ppowmod(base, e, m, p):
    result, base = [1], pdivmod(base, m, p)[1]
    while e:
        if e & 1:
            result = pmulmod(result, base, m, p)
        base = pmulmod(base, base, m, p)
        e >>= 1
    return result


def pgcd(a, b, p):
    while b:
        a, b = b, pdivmod(a, b, p)[1]
    inv = pow(a[-1], -1, p)
    return [c * inv % p for c in a]


def minus(h, c, k, p):
    """h - c*z^k."""
    h = h + [0] * (k + 1 - len(h))
    h[k] = (h[k] - c) % p
    return trim(h)


# ---- the four steps --------------------------------------------------------------------------
def berlekamp_massey(s, p):
    """Shortest [1, c1..cL] with s[n] + c1*s[n-1] + ... + cL*s[n-L] = 0 (mod p) for all n >= L."""
    C, B, L, m, b = [1], [1], 0, 1, 1
    for n in range(len(s)):
        d = sum(C[i] * s[n - i] for i in range(L + 1)) % p
        if d:
            T, coef = C[:], d * pow(b, -1, p) % p
            C += [0] * (len(B) + m - len(C))
            for i, Bi in enumerate(B):
                C[i + m] = (C[i + m] - coef * Bi) % p
            if 2 * L <= n:
                L, B, b, m = n + 1 - L, T, d, 0
        m += 1
        C += [0] * (L + 1 - len(C))
    return C[:L + 1]


def roots(f, p, rng):
    """Roots of a monic f that is a product of distinct linear factors over F_p (Cantor-Zassenhaus)."""
    if len(f) <= 2:
        return [-f[0] % p] if len(f) == 2 else []
    while True:
        h = ppowmod([rng.randrange(p), 1], (p - 1) // 2, f, p)      # (z + a)^((p-1)/2) mod f
        g = pgcd(f, minus(h, 1, 0, p), p)
        if 1 < len(g) < len(f):
            return roots(g, p, rng) + roots(pdivmod(f, g, p)[0], p, rng)


def exponents(m, max_deg):
    expo = []
    for q in PRIMES:
        e = 0
        while m and m % q == 0:
            m, e = m // q, e + 1
        expo.append(e)
    if m != 1 or max(expo) > max_deg:
        raise ValueError("a locator root is not a monomial value")
    return expo


def solve_linear(A, rhs, p):
    """Gauss-Jordan mod p for a square, invertible A."""
    n = len(A)
    M = [row[:] + [r] for row, r in zip(A, rhs)]
    for col in range(n):
        piv = next(r for r in range(col, n) if M[r][col])
        M[col], M[piv] = M[piv], M[col]
        inv = pow(M[col][col], -1, p)
        M[col] = [v * inv % p for v in M[col]]
        for r in range(n):
            if r != col and M[r][col]:
                k = M[r][col]
                M[r] = [(vr - k * vc) % p for vr, vc in zip(M[r], M[col])]
    return [row[n] for row in M]


def recover(values, p, max_deg):
    """Terms [e0..e5, coeff] of f from v_i = f(2^i, 3^i, 5^i, 7^i, 11^i, 13^i), i = 0..len(values)-1."""
    locator = berlekamp_massey(values, p)[::-1]     # z^t + c1 z^(t-1) + ... + ct = prod (z - m_j)
    t = len(locator) - 1
    if 2 * t > len(values):
        raise ValueError("too few evaluations to pin down the recurrence")
    if t and len(pgcd(locator, minus(ppowmod([0, 1], p, locator, p), 1, 1, p), p)) != t + 1:
        raise ValueError("locator does not split into distinct linear factors")   # gcd with z^p - z
    ms = sorted(roots(locator, p, random.Random(SEED)))
    expos = [exponents(m, max_deg) for m in ms]
    coeffs = solve_linear([[pow(m, i, p) for m in ms] for i in range(t)], values[:t], p)
    for i, v in enumerate(values):                  # the other evaluations are a free cross-check
        if sum(c * pow(m, i, p) for c, m in zip(coeffs, ms)) % p != v:
            raise ValueError("recovered polynomial disagrees with evaluation %d" % i)
    return [e + [c] for e, c in zip(expos, coeffs)]


def main():
    info = call("/")
    p, max_deg, max_terms = int(info["p"]), info["max_degree_per_variable"], info["max_terms"]
    need, left = 2 * max_terms, info["budget"]["remaining"]
    say("[solve] %s: %d-bit p, %d variables, degree <= %d each, <= %d terms, %d/%d evaluations left"
        % (BASE, p.bit_length(), info["variables"], max_deg, max_terms, left, info["budget"]["evaluations"]))
    if info["variables"] != len(PRIMES) or p <= math.prod(PRIMES) ** max_deg:
        sys.exit("[solve] unsupported parameters: need 6 variables and p > 30030^max_degree")
    if left < need:
        sys.exit("[solve] need %d evaluations, only %d left: this instance is spent; "
                 "`make reset` (or `make check`) draws a fresh one" % (need, left))
    values = [call("/eval", {"x": [pow(q, i, p) for q in PRIMES]})["y"] for i in range(need)]
    say("[solve] spent %d evaluations at x_i = (2^i, 3^i, 5^i, 7^i, 11^i, 13^i)" % need)
    terms = recover(values, p, max_deg)
    say("[solve] recovered %d terms; exponent vectors: %s"
        % (len(terms), " ".join("(%s)" % ",".join(map(str, t[:-1])) for t in terms)))
    reply = call("/submit", {"terms": terms})
    if not reply.get("solved"):
        sys.exit("[solve] submission rejected: %r" % reply)
    say("[solve] submission accepted")
    say("TOKEN: " + reply["token"])


if __name__ == "__main__":
    main()
