#!/usr/bin/env python3
"""
fathom -- the puzzle service.

A sounding line over a trench. At startup the service draws a secret sextic

    P(x) = c0 + c1*x + ... + c6*x^6      integers, |ci| <= 100000,

primitive, c6 > 0, irreducible over Q, with at least one real root. The
reading on the gauge is alpha, the largest real root of P. A visitor may pay
out as much line as they like, i.e. ask for digits of alpha, and nothing else:

    GET  /                          what this is, the bounds, the endpoints
    POST /digits {"n": k}           -> {"digits": floor(alpha * 10^k)}
    POST /submit {"coeffs": [...]}  -> {"solved": true, "token": "FLAG{...}"}
                                       or {"solved": false}

P is never sent anywhere and never logged. Every digit is exact: the service
never holds alpha as a float. It holds P, plus one rational number `lo` that
sits strictly between the second-largest real root and alpha (found once at
startup with a Sturm chain), and it answers a digit request by integer
bisection on the exact sign of P.

Standard library + Flask only. P and the token are fresh on every start.
"""
import math
import secrets
import threading
from fractions import Fraction

from flask import Flask, jsonify, request

DEGREE = 6
HEIGHT = 100_000          # every |ci| <= HEIGHT
MAX_N = 1000              # most digits after the point one request may ask for
PRIME_LIMIT = 400         # primes used for the irreducibility certificate


# ----------------------------------------------------------------------------
#  Polynomials over GF(p): coefficient lists, lowest degree first, no
#  trailing zeros, [] is the zero polynomial. Degree 6, so nothing clever.
# ----------------------------------------------------------------------------
def _primes_below(limit):
    sieve = bytearray([1]) * limit
    sieve[0:2] = b"\x00\x00"
    for i in range(2, int(limit ** 0.5) + 1):
        if sieve[i]:
            sieve[i * i::i] = bytearray(len(sieve[i * i::i]))
    return [i for i in range(limit) if sieve[i]]


PRIMES = _primes_below(PRIME_LIMIT)


def _trim(a):
    while a and a[-1] == 0:
        a.pop()
    return a


def _monic(a, p):
    inv = pow(a[-1], -1, p)
    return [(x * inv) % p for x in a]


def _rem(a, f, p):
    """a mod f over GF(p); f monic."""
    a = a[:]
    df = len(f) - 1
    for i in range(len(a) - 1, df - 1, -1):
        c = a[i]
        if c:
            for j in range(df + 1):
                a[i - df + j] = (a[i - df + j] - c * f[j]) % p
    return _trim(a[:df])


def _quo(a, g, p):
    """Exact quotient a / g over GF(p); g monic and g | a."""
    a = a[:]
    dg = len(g) - 1
    q = [0] * (len(a) - dg)
    for i in range(len(a) - 1, dg - 1, -1):
        c = a[i]
        q[i - dg] = c
        if c:
            for j in range(dg + 1):
                a[i - dg + j] = (a[i - dg + j] - c * g[j]) % p
    return _trim(q)


def _mulmod(a, b, f, p):
    if not a or not b:
        return []
    out = [0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        if x:
            for j, y in enumerate(b):
                out[i + j] = (out[i + j] + x * y) % p
    return _rem(out, f, p)


def _powmod(h, e, f, p):
    result = _rem([1], f, p)
    while e:
        if e & 1:
            result = _mulmod(result, h, f, p)
        h = _mulmod(h, h, f, p)
        e >>= 1
    return result


def _gcd(a, b, p):
    a, b = _trim(a[:]), _trim(b[:])
    while b:
        b = _monic(b, p)
        a, b = b, _rem(a, b, p)
    return _monic(a, p) if a else []


def degree_pattern(coeffs, p):
    """
    Degrees of the irreducible factors of P mod p (distinct-degree
    factorisation), or None when p tells us nothing: p divides the leading
    coefficient, or P mod p has a repeated factor.
    """
    f = [c % p for c in coeffs]
    if f[-1] == 0:
        return None
    f = _monic(f, p)
    deriv = _trim([(i * f[i]) % p for i in range(1, len(f))])
    if not deriv or len(_gcd(f, deriv, p)) != 1:
        return None
    pattern = []
    h = [0, 1]                                  # x^(p^d) mod f
    d = 0
    while len(f) - 1 >= 2 * (d + 1):
        d += 1
        h = _powmod(h, p, f, p)
        diff = h[:] + [0] * (2 - len(h))
        diff[1] = (diff[1] - 1) % p             # x^(p^d) - x
        g = _gcd(f, _trim(diff), p)
        if len(g) > 1:
            pattern += [d] * ((len(g) - 1) // d)
            f = _quo(f, g, p)
            h = _rem(h, f, p)
    if len(f) > 1:                              # what is left is one factor
        pattern.append(len(f) - 1)
    return sorted(pattern)


def irreducible_certificate(coeffs):
    """
    True only if P is provably irreducible over Q.

    A rational factor of degree d reduces, for every usable prime p, to a
    product of some of the factors of P mod p, so d is a subset sum of each
    degree pattern. If the only degrees that survive every prime are 0 and
    deg P, there is no proper factor. (False means "no proof found", which
    for a random sextic is rare; the caller just draws again.)
    """
    n = len(coeffs) - 1
    possible = set(range(n + 1))
    for p in PRIMES:
        pattern = degree_pattern(coeffs, p)
        if pattern is None:
            continue
        sums = {0}
        for d in pattern:
            sums |= {s + d for s in sums}
        possible &= sums
        if possible == {0, n}:
            return True
    return False


# ----------------------------------------------------------------------------
#  Real roots, exactly: a Sturm chain with integer coefficients.
# ----------------------------------------------------------------------------
def _neg_rem(a, b):
    """-(a mod b), rescaled by a positive constant to primitive integers."""
    a = [Fraction(x) for x in a]
    db = len(b) - 1
    lead = Fraction(b[-1])
    for i in range(len(a) - 1, db - 1, -1):
        q = a[i] / lead
        if q:
            for j in range(db + 1):
                a[i - db + j] -= q * b[j]
    r = _trim(a[:db])
    if not r:
        return []
    den = math.lcm(*[x.denominator for x in r])
    ints = [-int(x * den) for x in r]
    g = math.gcd(*ints)
    return [x // g for x in ints]


def sturm_chain(coeffs):
    chain = [list(coeffs), [i * coeffs[i] for i in range(1, len(coeffs))]]
    while len(chain[-1]) > 1:
        r = _neg_rem(chain[-2], chain[-1])
        if not r:               # repeated root: impossible for irreducible P
            break
        chain.append(r)
    return chain


def _sign_at(poly, num, den):
    """Sign of poly(num/den) for integer poly and den > 0. Exact."""
    acc, dpow = 0, 1
    for c in reversed(poly):
        acc = acc * num + c * dpow
        dpow *= den
    return (acc > 0) - (acc < 0)


def _variations(chain, x):
    signs = [s for s in (_sign_at(q, x.numerator, x.denominator) for q in chain) if s]
    return sum(1 for u, v in zip(signs, signs[1:]) if u != v)


def isolate_largest_root(coeffs):
    """
    Returns (lo, bound) with  lo < alpha < bound  and no other real root of P
    in [lo, +inf), where alpha is the largest real root. None if P has no
    real root. P must be squarefree with no rational root (true for an
    irreducible sextic), so P(lo) < 0 < P(bound) when the leading
    coefficient is positive.
    """
    chain = sturm_chain(coeffs)
    # Cauchy: every root has |x| < 1 + max|ci/cn|.
    bound = 2 + max(abs(c) for c in coeffs[:-1]) // abs(coeffs[-1])
    a, b = Fraction(-bound), Fraction(bound)
    vb = _variations(chain, b)
    if _variations(chain, a) - vb == 0:
        return None
    # Invariant: no root in (b, +inf), at least one in (a, b].
    while _variations(chain, a) - vb > 1:
        m = (a + b) / 2
        vm = _variations(chain, m)
        if vm - vb >= 1:
            a = m
        else:
            b, vb = m, vm
    return a, bound


# ----------------------------------------------------------------------------
#  The secret
# ----------------------------------------------------------------------------
def draw_polynomial(rng):
    """A fresh P (canonical: primitive, c6 > 0) plus its isolating data."""
    while True:
        c = [rng.randint(-HEIGHT, HEIGHT) for _ in range(DEGREE + 1)]
        if c[-1] == 0:
            continue
        if c[-1] < 0:
            c = [-x for x in c]
        if math.gcd(*c) != 1:
            continue
        if not irreducible_certificate(c):
            continue
        iso = isolate_largest_root(c)
        if iso is None:
            continue
        return c, iso[0], iso[1]


class Gauge:
    """Exact digits of alpha = largest real root of P."""

    def __init__(self, coeffs, lo, bound):
        self.coeffs = list(coeffs)
        self.lo = lo                    # rational, second root < lo < alpha
        self.lock = threading.Lock()
        assert self.coeffs[-1] > 0
        assert _sign_at(self.coeffs, lo.numerator, lo.denominator) < 0
        assert _sign_at(self.coeffs, bound, 1) > 0
        # Best reading so far: floor(alpha * 10^k) == m.
        self.k = 0
        self.m = self._bisect(0, math.floor(lo), bound)

    def _below_alpha(self, m, pows):
        """Is m / 10^k < alpha? Valid for m / 10^k > lo: there P < 0 iff x < alpha."""
        c = self.coeffs
        acc = c[DEGREE]
        for i in range(DEGREE - 1, -1, -1):
            acc = acc * m + c[i] * pows[i]      # 10^(6k) * P(m / 10^k), an integer
        return acc < 0

    def _bisect(self, k, low, high):
        """low/10^k < alpha < high/10^k, every integer above low is > lo*10^k."""
        scale = 10 ** k
        pows = [scale ** (DEGREE - i) for i in range(DEGREE + 1)]
        while high - low > 1:
            mid = (low + high) // 2
            if self._below_alpha(mid, pows):
                low = mid
            else:
                high = mid
        return low

    def digits(self, k):
        """floor(alpha * 10^k), exactly."""
        with self.lock:
            if k <= self.k:
                return self.m // 10 ** (self.k - k)
            step = 10 ** (k - self.k)
            floor_lo = (self.lo.numerator * 10 ** k) // self.lo.denominator
            low = max(self.m * step, floor_lo)
            high = (self.m + 1) * step
            self.m = self._bisect(k, low, high)
            self.k = k
            return self.m


# ----------------------------------------------------------------------------
#  HTTP
# ----------------------------------------------------------------------------
def build_app(gauge, token):
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024
    app.json.sort_keys = False
    secret = list(gauge.coeffs)

    def bad(msg, code=400):
        return jsonify({"error": msg}), code

    def is_int(x):
        return isinstance(x, int) and not isinstance(x, bool)

    @app.get("/")
    def index():
        return jsonify({
            "name": "fathom",
            "about": (
                "A sounding line over a trench. The gauge reads alpha, a real "
                "number that is the largest real root of a hidden polynomial P. "
                "You may pay out as much line as you like (ask for digits of "
                "alpha). Name P to get the token."
            ),
            "secret": {
                "degree": DEGREE,
                "height_bound": HEIGHT,
                "shape": "P(x) = c0 + c1*x + c2*x^2 + c3*x^3 + c4*x^4 + c5*x^5 + c6*x^6",
                "coefficients": "integers, |ci| <= %d for every i, c6 != 0" % HEIGHT,
                "irreducible_over_Q": True,
                "normalization": "primitive (gcd(c0..c6) = 1) and c6 > 0",
                "alpha": "the largest real root of P (P has at least one)",
                "fresh": "P and the token are redrawn every time the service starts",
            },
            "candidates": "(2*%d + 1)^7, about 1.28e37 coefficient vectors" % HEIGHT,
            "endpoints": {
                "GET /": "this document",
                "POST /digits": {
                    "body": {"n": "integer, 0 <= n <= %d" % MAX_N},
                    "returns": {
                        "n": "the n you sent",
                        "digits": "floor(alpha * 10^n) as an exact JSON integer",
                        "digits_str": "the same integer as a decimal string",
                    },
                    "notes": [
                        "exact to n places after the point, never rounded",
                        "floor rounds toward minus infinity, so the value is "
                        "negative when alpha is negative",
                        "the integer can be far wider than a 64-bit float; "
                        "parse it as a big integer or use digits_str",
                    ],
                },
                "POST /submit": {
                    "body": {"coeffs": "[c0, c1, c2, c3, c4, c5, c6], integers, in the normalization above"},
                    "returns": "{\"solved\": true, \"token\": \"FLAG{...}\"} if these are exactly "
                               "the coefficients of P, else {\"solved\": false}",
                    "notes": ["constant term first", "-P or a multiple of P is not accepted"],
                },
            },
            "limits": {"max_n": MAX_N},
        })

    @app.post("/digits")
    def digits():
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or "n" not in body:
            return bad('send JSON like {"n": 20}')
        n = body["n"]
        if not is_int(n) or n < 0 or n > MAX_N:
            return bad("n must be an integer with 0 <= n <= %d" % MAX_N)
        value = gauge.digits(n)
        return jsonify({"n": n, "digits": value, "digits_str": str(value)})

    @app.post("/submit")
    def submit():
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or "coeffs" not in body:
            return bad('send JSON like {"coeffs": [c0, c1, c2, c3, c4, c5, c6]}')
        coeffs = body["coeffs"]
        if (not isinstance(coeffs, list) or len(coeffs) != DEGREE + 1
                or not all(is_int(c) for c in coeffs)):
            return bad("coeffs must be a list of exactly %d integers, c0 first" % (DEGREE + 1))
        if coeffs == secret:
            return jsonify({"solved": True, "token": token})
        return jsonify({"solved": False})

    @app.errorhandler(404)
    def not_found(_exc):
        return bad("no such endpoint; see GET /", 404)

    @app.errorhandler(405)
    def wrong_method(_exc):
        return bad("wrong method; see GET /", 405)

    @app.errorhandler(413)
    def too_large(_exc):
        return bad("request body too large", 413)

    return app


def main():
    rng = secrets.SystemRandom()
    coeffs, lo, bound = draw_polynomial(rng)
    gauge = Gauge(coeffs, lo, bound)
    token = "FLAG{%s}" % secrets.token_hex(16)
    app = build_app(gauge, token)
    print("[fathom] secret drawn; listening on :80", flush=True)
    app.run(host="0.0.0.0", port=80, threaded=True)


if __name__ == "__main__":
    main()
