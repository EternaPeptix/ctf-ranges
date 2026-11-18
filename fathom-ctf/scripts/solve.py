#!/usr/bin/env python3
"""
fathom -- reference solver.

The service hides an irreducible integer sextic P (|ci| <= 100000) and hands
out exact digits of alpha, its largest real root. This script recovers P from
those digits alone, the way a player has to:

  1. GET /  -> degree, coefficient height bound, digit limit.
  2. POST /digits {"n": k}  -> A = floor(alpha * 10^k), so a = A / 10^k is
     within 10^-k of alpha.
  3. Build the 7 x 8 integer lattice with rows

         b_i = ( round(10^s * a^i),  e_i )        i = 0..6,   s < k

     A lattice vector is (sum c_i R_i, c0, ..., c6). For c = coefficients of
     P the first coordinate is 10^s * P(alpha) plus rounding noise, i.e. tiny,
     so (noise, P) is an abnormally short vector; every other coefficient
     vector of comparable size leaves a first coordinate of order 10^s times
     something that cannot be small.
  4. Exact integer LLL (pure Python, big integers, no floats) on that basis.
     The short vector's last seven coordinates are +-P.
  5. Check the candidate: degree 6, height within the bound, it changes sign
     across [B, B + 1] / 10^K for a second, longer reading B (extra digits it
     never saw), and it is provably irreducible (factor-degree patterns
     modulo small primes).
  6. POST /submit in canonical form (primitive, c6 > 0), print  TOKEN: <token>

How many digits: s >= 75 with k >= s + 34 makes the LLL output *provably*
+-P for every polynomial the service can draw (see organizer/SOLUTION.md);
the solver adds a small margin and uses s = 80, k = 120. If a run ever
failed, the loop in main() simply retries with more digits.

Standard library only. Override the target with FATHOM_URL
(e.g. http://localhost:9700 from the host).
"""
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request

BASE = os.environ.get("FATHOM_URL", "http://app").rstrip("/")

VERIFY_EXTRA = 40           # extra digits, beyond the lattice's k, used only to check
PRIME_LIMIT = 400           # primes tried for the irreducibility proof


def provable_digits(degree, height):
    """
    (s, g): weight 10^s and g guard digits for which LLL's first vector is
    guaranteed to be +-P, for any irreducible P of this degree and height.
    Derivation in organizer/SOLUTION.md; for degree 6, height 1e5: (75, 34).
    """
    n = degree + 1
    target = height * math.sqrt(n + (n / 2) ** 2)       # |(noise, P)| at most this
    reach = 2 ** ((n - 1) / 2) * target                 # LLL's b_1 is no longer than this
    l1 = math.sqrt(n) * reach                           # 1-norm of any rival that short
    # a rival D has |D(alpha)| >= 1 / (l1^(degree-1) * (sqrt(n)*height)^degree)
    s = math.log10(reach + l1 / 2 + 1) + (degree - 1) * math.log10(l1) \
        + degree * math.log10(math.sqrt(n) * height)
    # the unread tail of alpha must not move a rival's first coordinate by 1/2;
    # Cauchy: |alpha| < height + 1
    g = math.log10(2 * degree * l1) + (degree - 1) * math.log10(height + 2)
    return math.ceil(s), math.ceil(g)


def schedule(degree, height):
    """(s, g) to try, in order: the provable pair plus a margin, then more."""
    s, g = provable_digits(degree, height)
    return [(s + 5, g + 6), (s + 35, g + 16), (s + 75, g + 26)]


def say(msg):
    print(msg, flush=True)


# ----------------------------------------------------------------------------
#  HTTP
# ----------------------------------------------------------------------------
def call(path, body=None, tries=6, pause=0.2):
    """One JSON request. Every endpoint is idempotent, so retrying is safe."""
    data = None if body is None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json"} if data else {}
    last = None
    for attempt in range(1, tries + 1):
        try:
            req = urllib.request.Request(BASE + path, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise SystemExit("HTTP %d from %s: %s" % (exc.code, path, detail))
        except (urllib.error.URLError, OSError, ValueError) as exc:
            last = exc
            time.sleep(pause * attempt)
    raise SystemExit("no answer from %s%s: %s" % (BASE, path, last))


def wait_for_service(seconds=60):
    """The box may still be starting right after `make up` / `make reset`."""
    deadline = time.time() + seconds
    while True:
        try:
            with urllib.request.urlopen(BASE + "/", timeout=5) as resp:
                return json.loads(resp.read().decode())
        except (urllib.error.URLError, OSError, ValueError) as exc:
            if time.time() > deadline:
                raise SystemExit("service at %s never came up: %s" % (BASE, exc))
            time.sleep(0.5)


def read_digits(n):
    """floor(alpha * 10^n) as an exact Python integer."""
    reply = call("/digits", {"n": n})
    value = reply["digits"]
    if not isinstance(value, int) or isinstance(value, bool):
        raise SystemExit("unexpected /digits reply: %r" % (reply,))
    return value


# ----------------------------------------------------------------------------
#  Exact integer LLL
# ----------------------------------------------------------------------------
def lll_reduce(basis):
    """
    LLL-reduce the rows of `basis` (linearly independent integer vectors),
    delta = 3/4. All-integer variant (de Weger; Cohen, Alg. 2.6.7): instead of
    the rational Gram-Schmidt data it carries

        D[i]      = Gram determinant of the first i rows  (D[0] = 1)
        lam[i][j] = D[j+1] * mu[i][j]                     (j < i)

    which are integers, and every division below is exact. No floats, so the
    result is the true LLL basis no matter how long the entries are.
    """
    b = [list(row) for row in basis]
    n = len(b)
    D = [1] + [0] * n
    lam = [[0] * n for _ in range(n)]

    def dot(u, v):
        return sum(x * y for x, y in zip(u, v))

    def size_reduce(k, l):
        if 2 * abs(lam[k][l]) > D[l + 1]:
            q = (2 * lam[k][l] + D[l + 1]) // (2 * D[l + 1])    # nearest integer
            b[k] = [x - q * y for x, y in zip(b[k], b[l])]
            lam[k][l] -= q * D[l + 1]
            for i in range(l):
                lam[k][i] -= q * lam[l][i]

    def swap(k, kmax):
        b[k], b[k - 1] = b[k - 1], b[k]
        for j in range(k - 1):
            lam[k][j], lam[k - 1][j] = lam[k - 1][j], lam[k][j]
        lm = lam[k][k - 1]
        new_d = (D[k - 1] * D[k + 1] + lm * lm) // D[k]
        for i in range(k + 1, kmax + 1):
            t = lam[i][k]
            lam[i][k] = (D[k + 1] * lam[i][k - 1] - lm * t) // D[k]
            lam[i][k - 1] = (new_d * t + lm * lam[i][k]) // D[k + 1]
        D[k] = new_d

    D[1] = dot(b[0], b[0])
    if D[1] == 0:
        raise ValueError("zero vector in basis")
    k, kmax = 1, 0
    while k < n:
        if k > kmax:                                # bring row k into the GS data
            kmax = k
            for j in range(k + 1):
                u = dot(b[k], b[j])
                for i in range(j):
                    u = (D[i + 1] * u - lam[k][i] * lam[j][i]) // D[i]
                if j < k:
                    lam[k][j] = u
                else:
                    if u == 0:
                        raise ValueError("basis rows are linearly dependent")
                    D[k + 1] = u
        size_reduce(k, k - 1)
        # Lovasz: |b*_k|^2 >= (3/4 - mu^2) |b*_{k-1}|^2, cleared of denominators.
        if 4 * D[k + 1] * D[k - 1] < 3 * D[k] * D[k] - 4 * lam[k][k - 1] ** 2:
            swap(k, kmax)
            k = max(1, k - 1)
        else:
            for l in range(k - 2, -1, -1):
                size_reduce(k, l)
            k += 1
    return b


# ----------------------------------------------------------------------------
#  The lattice
# ----------------------------------------------------------------------------
def scaled_powers(A, k, s, degree):
    """R_i = round(10^s * (A / 10^k)^i) for i = 0..degree, exactly (needs k >= s)."""
    out = [10 ** s]
    num = 1
    for i in range(1, degree + 1):
        num *= A
        den = 10 ** (k * i - s)
        out.append((2 * num + den) // (2 * den))
    return out


def relation_basis(A, k, s, degree):
    """Rows (R_i, e_i): the first coordinate carries the weight 10^s."""
    powers = scaled_powers(A, k, s, degree)
    n = degree + 1
    return [[powers[i]] + [1 if j == i else 0 for j in range(n)] for i in range(n)]


def canonical(coeffs):
    """Primitive, positive leading coefficient."""
    g = math.gcd(*coeffs)
    out = [c // g for c in coeffs]
    if out[-1] < 0:
        out = [-c for c in out]
    return out


def sign_at(coeffs, num, den):
    """Sign of Q(num / den), den > 0. Exact."""
    acc, dpow = 0, 1
    for c in reversed(coeffs):
        acc = acc * num + c * dpow
        dpow *= den
    return (acc > 0) - (acc < 0)


# ----------------------------------------------------------------------------
#  Irreducibility over Q: factor-degree patterns modulo small primes.
#  Polynomials over GF(p) are coefficient lists, lowest degree first.
# ----------------------------------------------------------------------------
def _primes_below(limit):
    return [q for q in range(2, limit) if all(q % r for r in range(2, int(q ** 0.5) + 1))]


def _trim(a):
    while a and a[-1] == 0:
        a.pop()
    return a


def _monic(a, p):
    inv = pow(a[-1], -1, p)
    return [(x * inv) % p for x in a]


def _divmod(a, f, p):
    """Quotient and remainder of a by monic f over GF(p)."""
    a = a[:]
    df = len(f) - 1
    q = [0] * max(0, len(a) - df)
    for i in range(len(a) - 1, df - 1, -1):
        c = a[i]
        q[i - df] = c
        if c:
            for j in range(df + 1):
                a[i - df + j] = (a[i - df + j] - c * f[j]) % p
    return _trim(q), _trim(a[:df])


def _mulmod(a, b, f, p):
    if not a or not b:
        return []
    out = [0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        if x:
            for j, y in enumerate(b):
                out[i + j] = (out[i + j] + x * y) % p
    return _divmod(out, f, p)[1]


def _powmod(h, e, f, p):
    result = _divmod([1], f, p)[1]
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
        a, b = b, _divmod(a, b, p)[1]
    return _monic(a, p) if a else []


def degree_pattern(coeffs, p):
    """Degrees of the irreducible factors of Q mod p, or None if p is unusable."""
    f = [c % p for c in coeffs]
    if f[-1] == 0:
        return None
    f = _monic(f, p)
    deriv = _trim([(i * f[i]) % p for i in range(1, len(f))])
    if not deriv or len(_gcd(f, deriv, p)) != 1:
        return None                             # repeated factor mod p
    pattern = []
    h = [0, 1]                                  # x^(p^d) mod f
    d = 0
    while len(f) - 1 >= 2 * (d + 1):
        d += 1
        h = _powmod(h, p, f, p)
        diff = h[:] + [0] * (2 - len(h))
        diff[1] = (diff[1] - 1) % p
        g = _gcd(f, _trim(diff), p)             # product of the degree-d factors
        if len(g) > 1:
            pattern += [d] * ((len(g) - 1) // d)
            f = _divmod(f, g, p)[0]
            h = _divmod(h, f, p)[1]
    if len(f) > 1:
        pattern.append(len(f) - 1)
    return sorted(pattern)


def provably_irreducible(coeffs):
    """
    A rational factor of degree d must, modulo every usable prime, be a
    product of some of the factors there, so d is a subset sum of every
    degree pattern. If only 0 and deg Q survive, Q is irreducible over Q.
    """
    n = len(coeffs) - 1
    possible = set(range(n + 1))
    for p in _primes_below(PRIME_LIMIT):
        pattern = degree_pattern(coeffs, p)
        if pattern is None:
            continue
        sums = {0}
        for d in pattern:
            sums |= {t + d for t in sums}
        possible &= sums
        if possible == {0, n}:
            return True
    return False


# ----------------------------------------------------------------------------
#  Recovery
# ----------------------------------------------------------------------------
def recover(oracle, degree, height, s, guard, log=say):
    """
    One attempt. `oracle(n)` returns floor(alpha * 10^n). Returns the
    canonical coefficient list [c0..c_degree] or None.
    """
    k = s + guard
    A = oracle(k)
    log("[solve] read %d digits after the point: alpha = %s" % (k, preview(A, k)))

    basis = relation_basis(A, k, s, degree)
    t0 = time.time()
    reduced = lll_reduce(basis)
    log("[solve] LLL on the %dx%d basis (entries up to %d digits, weight 10^%d): %.3fs"
        % (len(basis), len(basis[0]), max(len(str(abs(r[0]))) for r in basis), s, time.time() - t0))

    K = k + VERIFY_EXTRA
    B = None
    for row in sorted(reduced, key=lambda r: sum(x * x for x in r)):
        coeffs = row[1:]
        if coeffs[-1] == 0 or max(abs(c) for c in coeffs) > height:
            continue
        cand = canonical(coeffs)
        if B is None:
            B = oracle(K)                       # digits the lattice never saw
            if B // 10 ** (K - k) != A:
                raise SystemExit("the two readings disagree; service misbehaving")
        # alpha is in (B, B+1)/10^K and is the largest root: Q must go - to +.
        if not (sign_at(cand, B, 10 ** K) < 0 < sign_at(cand, B + 1, 10 ** K)):
            log("[solve] candidate rejected: no sign change at %d digits" % K)
            continue
        if not provably_irreducible(cand):
            log("[solve] candidate rejected: no irreducibility proof")
            continue
        log("[solve] candidate has height %d <= %d, degree %d, changes sign across the "
            "%d-digit reading, irreducible: accepted"
            % (max(abs(c) for c in cand), height, degree, K))
        return cand
    return None


def preview(A, k, shown=30):
    """Leading digits of alpha, given A = floor(alpha * 10^k), k >= 1."""
    # alpha lies in (A, A+1) / 10^k; for a negative reading |alpha| truncates to -A-1.
    sign, mag = ("-", -A - 1) if A < 0 else ("", A)
    text = str(mag).rjust(k + 1, "0")
    return "%s%s.%s..." % (sign, text[:-k], text[-k:][:shown])


def main():
    doc = wait_for_service()
    secret = doc.get("secret", {})
    degree = int(secret.get("degree", 6))
    height = int(secret.get("height_bound", 100000))
    max_n = int(doc.get("limits", {}).get("max_n", 1000))
    say("[solve] target %s: degree %d, |ci| <= %d, up to %d digits per request"
        % (BASE, degree, height, max_n))

    for s, guard in schedule(degree, height):
        if s + guard + VERIFY_EXTRA > max_n:
            break
        say("[solve] weight 10^%d, %d guard digits -> asking for k = %d digits"
            % (s, guard, s + guard))
        coeffs = recover(read_digits, degree, height, s, guard)
        if coeffs is None:
            say("[solve] no polynomial from %d digits; asking for more" % (s + guard))
            continue
        say("[solve] P = %s" % coeffs)
        reply = call("/submit", {"coeffs": coeffs})
        if reply.get("solved") and reply.get("token"):
            say("TOKEN: %s" % reply["token"])
            return 0
        say("[solve] /submit said no: %r" % (reply,))
    say("[solve] FAILED: polynomial not recovered")
    return 1


if __name__ == "__main__":
    sys.exit(main())
