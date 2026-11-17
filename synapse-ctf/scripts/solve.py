#!/usr/bin/env python3
"""
synapse -- reference solver.

Reconstructs the hidden piecewise-linear function f: Q^n -> Q exactly, using
nothing but POST /eval, then submits the reconstruction to POST /verify and
prints the completion token.

Pure standard library. Every number is a fractions.Fraction: there is no
floating point and no tolerance anywhere, only exact equality tests.

Method (details in organizer/SOLUTION.md):
  1. exact local gradients by central differences on a verified-linear stencil
  2. exact kink locations of F(t) = f(p + t d) on random lines
  3. one hyperplane (U, beta) per kink from the gradient jump across it,
     confirmed by independent probes elsewhere on that hyperplane
  4. exact rational linear solve for the output coefficients
  5. local cross-check on fresh points, then submit
"""
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from fractions import Fraction as Fr

BASE = os.environ.get("SYN_URL", "http://app").rstrip("/")
SEED = int(os.environ.get("SYN_SEED", "1"))

T = Fr(64)            # lines are scanned for t in [-T, T]
P_DEN = 1000003       # prime denominator of line base points (keeps kinks off dyadic split points)
MAX_DEPTH = 48        # bisection depth cap on a line
MAX_HALVINGS = 64     # step-halving cap for stencils
MAX_LINES = 200       # give up after this many random lines
PROBES = 2            # independent confirmations per candidate hyperplane
SELFCHECK_POINTS = 40

ZERO = Fr(0)
ONE = Fr(1)


class Degenerate(Exception):
    """A non-generic configuration was hit; the caller just moves on."""


# ----------------------------------------------------------------------------
# Query access
# ----------------------------------------------------------------------------
def _no_float(literal):
    raise ValueError("service sent a floating point literal: %r" % (literal,))


def fmt(q):
    return "%d/%d" % (q.numerator, q.denominator)


class Oracle:
    """Exact evaluation oracle for f, with a cache so no point is paid for twice."""

    def __init__(self, base):
        self.base = base
        self.cache = {}
        self.queries = 0

    def call(self, method, path, payload=None):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        last = None
        for _ in range(6):
            req = urllib.request.Request(
                self.base + path, data=data, method=method,
                headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return json.loads(resp.read().decode("utf-8"),
                                      parse_float=_no_float, parse_constant=_no_float)
            except urllib.error.HTTPError as err:          # the service answered: not transient
                raise RuntimeError("%s %s -> HTTP %d: %s" % (
                    method, path, err.code, err.read().decode("utf-8", "replace")[:200]))
            except (urllib.error.URLError, OSError) as err:
                last = err
                time.sleep(1)
        raise RuntimeError("%s %s failed: %s" % (method, path, last))

    def wait_ready(self, tries=90):
        for _ in range(tries):
            try:
                req = urllib.request.Request(self.base + "/", method="GET")
                with urllib.request.urlopen(req, timeout=5) as resp:
                    return json.loads(resp.read().decode("utf-8"),
                                      parse_float=_no_float, parse_constant=_no_float)
            except (urllib.error.URLError, OSError, ValueError):
                time.sleep(1)
        raise RuntimeError("service at %s never came up" % self.base)

    def evaluate(self, x):
        """One real query. Overridden by offline test harnesses."""
        return Fr(self.call("POST", "/eval", {"x": [fmt(c) for c in x]})["y"])

    def f(self, x):
        key = tuple(x)
        val = self.cache.get(key)
        if val is None:
            val = self.evaluate(x)
            self.queries += 1
            self.cache[key] = val
        return val


# ----------------------------------------------------------------------------
# Small exact helpers
# ----------------------------------------------------------------------------
def dot(u, v):
    return sum((a * b for a, b in zip(u, v)), ZERO)


def along(p, t, d):
    return [pi + t * di for pi, di in zip(p, d)]


def bump(x, i, step):
    y = list(x)
    y[i] = y[i] + step
    return y


def relu(v):
    return v if v > ZERO else ZERO


def show(q):
    return str(q.numerator) if q.denominator == 1 else fmt(q)


# ----------------------------------------------------------------------------
# Step 1: exact local gradient at a generic point
# ----------------------------------------------------------------------------
def gradient(orc, x, eps0):
    """
    Exact gradient of f at x. For each axis the step is halved until the
    5-point stencil x, x +- eps e_i, x +- (eps/2) e_i is exactly collinear;
    on a linear stencil the central difference IS the partial derivative.
    """
    fx = orc.f(x)
    grad = []
    for i in range(len(x)):
        eps = eps0
        for _ in range(MAX_HALVINGS):
            hi, lo = orc.f(bump(x, i, eps)), orc.f(bump(x, i, -eps))
            if hi + lo - 2 * fx == 0:
                half = eps / 2
                hi2, lo2 = orc.f(bump(x, i, half)), orc.f(bump(x, i, -half))
                if hi2 + lo2 - 2 * fx == 0 and hi - lo == 2 * (hi2 - lo2):
                    grad.append((hi - lo) / (2 * eps))
                    break
            eps = eps / 2
        else:
            raise Degenerate("no linear neighbourhood found")
    return grad


# ----------------------------------------------------------------------------
# Step 2: exact kinks of a piecewise-linear F on [lo, hi]
# ----------------------------------------------------------------------------
def find_kinks(F, lo, hi, out, depth=0):
    """
    Appends (t*, lo, hi) for every isolated kink: F is linear on [lo, t*] and
    on [t*, hi], with different slopes. Intervals that are not a clean single
    bend are bisected.
    """
    width = hi - lo
    f_lo, f_hi = F(lo), F(hi)
    chord = (f_hi - f_lo) / width
    mid = lo + width / 2
    if all(F(s) == f_lo + chord * (s - lo) for s in (mid, lo + width / 4, lo + 3 * width / 4)):
        return                                            # linear: nothing here
    if depth >= MAX_DEPTH:
        return                                            # degenerate cluster: skip it

    h = width / 16
    s_left = (F(lo + h) - f_lo) / h                       # slope just right of lo
    s_right = (f_hi - F(hi - h)) / h                      # slope just left of hi
    if s_left != s_right:
        # intersection of  f_lo + s_left (t - lo)  with  f_hi + s_right (t - hi)
        t = (f_hi - f_lo + s_left * lo - s_right * hi) / (s_left - s_right)
        if lo < t < hi and F(t) == f_lo + s_left * (t - lo):
            clean = True
            for k in (2, 8, 64):                          # both sides, three scales
                a = t - (t - lo) / k
                b = t + (hi - t) / k
                if F(a) != f_lo + s_left * (a - lo) or F(b) != f_hi + s_right * (b - hi):
                    clean = False
                    break
            if clean:
                out.append((t, lo, hi))
                return
    find_kinks(F, lo, mid, out, depth + 1)
    find_kinks(F, mid, hi, out, depth + 1)


# ----------------------------------------------------------------------------
# Step 3: hyperplanes
# ----------------------------------------------------------------------------
def canonical(U, beta):
    """Fix the sign: first nonzero component of U positive."""
    lead = next(c for c in U if c != 0)
    if lead < 0:
        U, beta = [-c for c in U], -beta
    return tuple(U), beta


def kink_at(orc, y, direction):
    """
    Is f bent exactly at y along `direction`? With S(eta) the second difference
    f(y + eta d) + f(y - eta d) - 2 f(y): a bend exactly at y makes S exactly
    proportional to eta once eta is small; no bend at y makes S vanish.
    """
    fy = orc.f(y)

    def second(eta):
        return orc.f(along(y, eta, direction)) + orc.f(along(y, -eta, direction)) - 2 * fy

    eta = Fr(1, 16)
    for _ in range(MAX_HALVINGS):
        s1, s2, s4 = second(eta), second(eta / 2), second(eta / 4)
        if s1 == 0 and s2 == 0 and s4 == 0:
            return False
        if s4 != 0 and s2 == 2 * s4 and s1 == 4 * s4:
            return True
        eta = eta / 2
    return False


def confirm_plane(orc, U, beta, rng):
    """Independent check: f must be bent at fresh random points of {U.x + beta = 0}."""
    n = len(U)
    pivot = max(range(n), key=lambda i: abs(U[i]))
    for _ in range(PROBES):
        y = [Fr(rng.randint(-4 * 9973, 4 * 9973), 9973) for _ in range(n)]
        rest = beta + sum((U[k] * y[k] for k in range(n) if k != pivot), ZERO)
        y[pivot] = -rest / U[pivot]                        # y is on the hyperplane
        while True:
            direction = [Fr(rng.randint(-9, 9)) for _ in range(n)]
            if dot(U, direction) != 0:                     # must cross the hyperplane
                break
        if not kink_at(orc, y, direction):
            return False
    return True


def shoot_line(orc, n, rng, planes, log):
    """Scan one random line; add every newly confirmed hyperplane to `planes`."""
    p = [Fr(rng.randint(-2 * P_DEN, 2 * P_DEN), P_DEN) for _ in range(n)]
    while True:
        d = [Fr(rng.randint(-9, 9)) for _ in range(n)]
        if any(d):
            break

    def F(t):
        return orc.f(along(p, t, d))

    kinks = []
    find_kinks(F, -T, T, kinks)
    new = rejected = 0
    for t, lo, hi in kinks:
        xk = along(p, t, d)
        if any(dot(U, xk) + beta == 0 for U, beta in planes):
            continue                                       # a hyperplane we already hold
        back, fwd = (t - lo) / 2, (hi - t) / 2
        eps0 = min(back, fwd)
        try:
            g_minus = gradient(orc, along(p, t - back, d), eps0)
            g_plus = gradient(orc, along(p, t + fwd, d), eps0)
        except Degenerate:
            rejected += 1
            continue
        U = [a - b for a, b in zip(g_plus, g_minus)]       # = (+-) a_j w_j
        if not any(U):
            rejected += 1
            continue
        key = canonical(U, -dot(U, xk))                    # beta = -U . x_k
        if key in planes:
            continue
        if confirm_plane(orc, key[0], key[1], rng):
            planes[key] = True
            new += 1
        else:
            rejected += 1
    log("  kinks on line: %d, new hyperplanes: %d, rejected candidates: %d, total: %d"
        % (len(kinks), new, rejected, len(planes)))


# ----------------------------------------------------------------------------
# Step 4: exact fit of the output coefficients
# ----------------------------------------------------------------------------
def solve_exact(rows, rhs):
    """
    Gauss-Jordan elimination over Q on a (possibly overdetermined) system.
    Returns (solution, rank); solution is None if the system is inconsistent.
    Free variables, if any, are set to 0.
    """
    m = len(rows[0])
    M = [list(r) + [b] for r, b in zip(rows, rhs)]
    pivots = []
    r = 0
    for c in range(m):
        pr = next((i for i in range(r, len(M)) if M[i][c] != 0), None)
        if pr is None:
            continue
        M[r], M[pr] = M[pr], M[r]
        inv = ONE / M[r][c]
        M[r] = [v * inv for v in M[r]]
        for i in range(len(M)):
            if i != r and M[i][c] != 0:
                fac = M[i][c]
                M[i] = [a - fac * b for a, b in zip(M[i], M[r])]
        pivots.append(c)
        r += 1
        if r == len(M):
            break
    if any(M[i][m] != 0 for i in range(r, len(M))):
        return None, r
    sol = [ZERO] * m
    for i, c in enumerate(pivots):
        sol[c] = M[i][m]
    return sol, r


def features(planes, x):
    return [relu(dot(U, x) + beta) for U, beta in planes] + list(x) + [ONE]


def fit(orc, n, rng, planes):
    """
    Solve f(x) = sum_j lambda_j max(0, U_j.x + beta_j) + L.x + e exactly.
    The system is 3x overdetermined, so a missing hyperplane shows up as an
    inconsistency rather than as a wrong answer.
    """
    planes = list(planes)
    unknowns = len(planes) + n + 1
    rows, rhs = [], []
    scales = (1, 2, 4, 8, 16)
    for round_no in range(4):
        for k in range(3 * unknowns):
            x = [Fr(rng.randint(-scales[k % 5] * 997, scales[k % 5] * 997), 997) for _ in range(n)]
            rows.append(features(planes, x))
            rhs.append(orc.f(x))
        sol, rank = solve_exact(rows, rhs)
        if sol is None:
            return None
        if rank == unknowns:
            break
    relus = [(U, beta, lam) for (U, beta), lam in zip(planes, sol)]
    lin = sol[len(planes):len(planes) + n]
    const = sol[-1]
    return relus, lin, const


def model_eval(model, x):
    relus, lin, const = model
    return const + dot(lin, x) + sum((lam * relu(dot(U, x) + beta) for U, beta, lam in relus), ZERO)


def self_check(orc, n, rng, model):
    for k in range(SELFCHECK_POINTS):
        scale = (1, 3, 9, 27)[k % 4]
        x = [Fr(rng.randint(-scale * 991, scale * 991), 991) for _ in range(n)]
        if model_eval(model, x) != orc.f(x):
            return False
    return True


# ----------------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------------
def reconstruct(orc, n, H, rng, log=lambda s: None):
    """Returns (relus, lin, const) with g == f, or raises."""
    planes = {}                                           # (U, beta) -> True, in discovery order
    for line_no in range(1, MAX_LINES + 1):
        log("line %d (queries so far: %d)" % (line_no, orc.queries))
        shoot_line(orc, n, rng, planes, log)
        if len(planes) < H:
            continue
        model = fit(orc, n, rng, planes)
        if model is None:
            log("  fit inconsistent: a hyperplane is still missing, shooting more lines")
            continue
        if not self_check(orc, n, rng, model):
            log("  local cross-check failed, shooting more lines")
            continue
        return model
    raise RuntimeError("could not reconstruct f within %d lines" % MAX_LINES)


def submission(model):
    relus, lin, const = model
    return {
        "relus": [{"q": [fmt(c) for c in U], "r": fmt(beta), "p": fmt(lam)}
                  for U, beta, lam in relus if lam != 0],
        "lin": [fmt(c) for c in lin],
        "const": fmt(const),
    }


def main():
    def log(msg):
        print(msg, flush=True)

    orc = Oracle(BASE)
    info = orc.wait_ready()
    n, H = int(info["n"]), int(info["H"])
    log("[solve] target %s: n=%d inputs, H=%d hidden units" % (BASE, n, H))

    rng = random.Random(SEED)                             # integer draws only
    model = reconstruct(orc, n, H, rng, log)
    relus, lin, const = model
    log("[solve] reconstruction (exact):")
    for U, beta, lam in relus:
        log("    (%s) * max(0, [%s] . x + (%s))" % (show(lam), ", ".join(show(c) for c in U), show(beta)))
    log("    + [%s] . x + (%s)" % (", ".join(show(c) for c in lin), show(const)))
    log("[solve] %d /eval queries, %d hyperplanes" % (orc.queries, len(relus)))

    verdict = orc.call("POST", "/verify", submission(model))
    if verdict.get("solved") is True and str(verdict.get("token", "")).startswith("FLAG{"):
        log("TOKEN: %s" % verdict["token"])
        log("[solve] SUCCESS: /verify accepted the reconstruction")
        return 0
    log("[solve] FAILURE: /verify said %s" % json.dumps(verdict))
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as err:                              # noqa: BLE001 - report and fail
        print("[solve] ERROR: %s" % err, flush=True)
        sys.exit(1)
