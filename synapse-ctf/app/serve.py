#!/usr/bin/env python3
"""
synapse -- a function-reconstruction puzzle.

The process holds a hidden piecewise-linear function f: Q^n -> Q, realised as a
one-hidden-layer ReLU network with secret integer parameters drawn fresh at
startup:

    f(x) = sum_{j=1..H} a_j * max(0, w_j . x + b_j) + c

It answers exact evaluation queries (POST /eval) and releases a completion
token (POST /verify) to anyone who submits a function that is exactly equal
to f.

All arithmetic is exact (fractions.Fraction). There is no floating point
anywhere: numbers travel as "num/den" strings, and a JSON float in a request
is rejected before it is ever turned into a number.
"""
import json
import logging
import re
import secrets
from fractions import Fraction

from flask import Flask, Response, request

# ----------------------------------------------------------------------------
# Public shape of the puzzle
# ----------------------------------------------------------------------------
N = 6                 # inputs
H = 10                # hidden units
PARAM_RANGE = 5       # every secret integer lies in [-PARAM_RANGE, PARAM_RANGE]

# /verify batch: fresh random rational points on every call
VERIFY_GENERIC = 200          # box points at mixed scales
VERIFY_NEAR_PER_UNIT = 20     # points hugging each kink surface, both sides
VERIFY_POINTS = VERIFY_GENERIC + H * VERIFY_NEAR_PER_UNIT   # = 400
VERIFY_SCALES = (1, 2, 4, 8, 16, 32)

# Request limits
MAX_NUM_CHARS = 1024          # characters per rational literal
MAX_RELUS = 64                # ReLU terms accepted in a submission
MAX_BODY_BYTES = 512 * 1024

ZERO = Fraction(0)


# ----------------------------------------------------------------------------
# Secrets (process memory only; regenerated on every start)
# ----------------------------------------------------------------------------
def _randint(lo, hi):
    """Uniform integer in [lo, hi] from the OS CSPRNG (integers only)."""
    return lo + secrets.randbelow(hi - lo + 1)


def _parallel(u, v):
    """True iff integer vectors u, v are linearly dependent (all 2x2 minors 0)."""
    return all(u[i] * v[j] - u[j] * v[i] == 0
               for i in range(N) for j in range(i + 1, N))


def _gen_network():
    rows = []
    while len(rows) < H:
        w = [_randint(-PARAM_RANGE, PARAM_RANGE) for _ in range(N)]
        if not any(w):
            continue                      # every row is nonzero
        if any(_parallel(w, v) for v in rows):
            continue                      # no two rows parallel (or anti-parallel)
        rows.append(w)
    bias = [_randint(-PARAM_RANGE, PARAM_RANGE) for _ in range(H)]
    out = []
    while len(out) < H:
        a = _randint(-PARAM_RANGE, PARAM_RANGE)
        if a != 0:
            out.append(a)                 # every output weight is nonzero
    const = _randint(-PARAM_RANGE, PARAM_RANGE)
    return rows, bias, out, const


W, B, A, C = _gen_network()
TOKEN = "FLAG{synapse_reconstruct_relu_net_" + secrets.token_hex(12) + "}"


def f(x):
    """The hidden function, evaluated exactly."""
    total = Fraction(C)
    for w, b, a in zip(W, B, A):
        pre = sum((wi * xi for wi, xi in zip(w, x)), Fraction(b))
        if pre > ZERO:
            total += a * pre
    return total


# ----------------------------------------------------------------------------
# Strict exact-rational parsing
# ----------------------------------------------------------------------------
class BadRequest(Exception):
    pass


_RATIONAL = re.compile(r"[+-]?[0-9]+(?:/[0-9]+)?\Z")


def _no_float(literal):
    raise BadRequest("floating point is not accepted; send integers or \"p/q\" strings")


def parse_rational(v):
    if isinstance(v, bool):
        raise BadRequest("booleans are not numbers")
    if isinstance(v, int):
        return Fraction(v)
    if isinstance(v, str):
        s = v.strip()
        if len(s) > MAX_NUM_CHARS:
            raise BadRequest("rational literal longer than %d characters" % MAX_NUM_CHARS)
        if not _RATIONAL.match(s):
            raise BadRequest("not an integer or \"p/q\" literal: %r" % s[:40])
        num, _, den = s.partition("/")
        den = int(den) if den else 1
        if den == 0:
            raise BadRequest("zero denominator")
        return Fraction(int(num), den)
    raise BadRequest("numbers must be integers or \"p/q\" strings")


def parse_vector(v, what):
    if not isinstance(v, list) or len(v) != N:
        raise BadRequest("%s must be a list of exactly %d rationals" % (what, N))
    return [parse_rational(c) for c in v]


def read_json():
    raw = request.get_data(cache=False)
    try:
        body = json.loads(raw.decode("utf-8"), parse_float=_no_float, parse_constant=_no_float)
    except BadRequest:
        raise
    except (ValueError, UnicodeDecodeError, RecursionError):
        raise BadRequest("body must be valid JSON")
    if not isinstance(body, dict):
        raise BadRequest("body must be a JSON object")
    return body


def fmt(q):
    return "%d/%d" % (q.numerator, q.denominator)


def reply(obj, status=200):
    return Response(json.dumps(obj), status=status, mimetype="application/json")


# ----------------------------------------------------------------------------
# Fresh verification points
# ----------------------------------------------------------------------------
def _rand_rational(scale):
    den = _randint(1, 1000)
    return Fraction(_randint(-scale * den, scale * den), den)


def fresh_points():
    pts = []
    # (1) generic points in boxes of several sizes
    for k in range(VERIFY_GENERIC):
        scale = VERIFY_SCALES[k % len(VERIFY_SCALES)]
        pts.append([_rand_rational(scale) for _ in range(N)])
    # (2) points right next to every kink surface, on both sides of it
    for w, b in zip(W, B):
        support = [i for i in range(N) if w[i] != 0]
        for _ in range(VERIFY_NEAR_PER_UNIT // 2):
            x = [_rand_rational(8) for _ in range(N)]
            i = support[_randint(0, len(support) - 1)]
            rest = sum((w[k] * x[k] for k in range(N) if k != i), Fraction(b))
            x[i] = -rest / w[i]                       # x now lies on the surface
            for sign in (1, -1):
                y = list(x)
                y[i] = x[i] + Fraction(sign, _randint(1, 10 ** 6))
                pts.append(y)
    return pts


# ----------------------------------------------------------------------------
# HTTP
# ----------------------------------------------------------------------------
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_BODY_BYTES


@app.errorhandler(BadRequest)
def _bad_request(err):
    return reply({"error": str(err)}, 400)


@app.errorhandler(404)
def _not_found(err):
    return reply({"error": "no such endpoint; see GET /"}, 404)


@app.errorhandler(405)
def _bad_method(err):
    return reply({"error": "method not allowed; see GET /"}, 405)


@app.errorhandler(413)
def _too_large(err):
    return reply({"error": "request body too large"}, 413)


@app.get("/")
def index():
    return reply({
        "name": "synapse",
        "puzzle": (
            "A hidden piecewise-linear function f: Q^n -> Q is held by this service. "
            "Reconstruct f exactly, as a function, using evaluation queries only, "
            "then submit your reconstruction to /verify to receive the completion token."
        ),
        "n": N,
        "H": H,
        "model": {
            "form": "f(x) = sum_{j=1..H} a_j * max(0, w_j . x + b_j) + c",
            "parameters": (
                "secret, fixed for the lifetime of the service: w_j in Z^n, b_j, a_j, c in Z, "
                "all of small magnitude; every a_j is nonzero, every w_j is nonzero, "
                "and no two w_j are parallel"
            ),
        },
        "domain": {
            "space": "Q^%d (every rational point is a valid input)" % N,
            "encoding": (
                "each coordinate is a JSON integer or a string \"p/q\" (also \"p\"), "
                "at most %d characters; JSON floats are rejected" % MAX_NUM_CHARS
            ),
        },
        "arithmetic": "exact rationals end to end; results are strings \"num/den\" in lowest terms",
        "endpoints": {
            "GET /": "this description",
            "POST /eval": {
                "request": "{\"x\": [x_1, ..., x_%d]}" % N,
                "response": "{\"y\": \"num/den\"}",
                "meaning": "y = f(x), exactly",
            },
            "POST /verify": {
                "request": (
                    "{\"relus\": [{\"q\": [q_1, ..., q_%d], \"r\": \"p/q\", \"p\": \"p/q\"}, ...], "
                    "\"lin\": [l_1, ..., l_%d], \"const\": \"p/q\"}" % (N, N)
                ),
                "meaning": (
                    "your function g(x) = sum_k p_k * max(0, q_k . x + r_k) + lin . x + const "
                    "(at most %d relu terms) is compared with f, exactly, on %d fresh random "
                    "rational points" % (MAX_RELUS, VERIFY_POINTS)
                ),
                "response": (
                    "{\"solved\": true, \"token\": \"FLAG{...}\"} if g(x) == f(x) at every point, "
                    "else {\"solved\": false, \"mismatches\": <count>}"
                ),
            },
        },
    })


@app.post("/eval")
def eval_endpoint():
    body = read_json()
    x = parse_vector(body.get("x"), "x")
    return reply({"y": fmt(f(x))})


@app.post("/verify")
def verify_endpoint():
    body = read_json()
    relus_in = body.get("relus", [])
    if not isinstance(relus_in, list) or len(relus_in) > MAX_RELUS:
        raise BadRequest("relus must be a list of at most %d terms" % MAX_RELUS)
    relus = []
    for term in relus_in:
        if not isinstance(term, dict):
            raise BadRequest("each relu term must be an object {q, r, p}")
        relus.append((
            parse_vector(term.get("q"), "relus[].q"),
            parse_rational(term.get("r", 0)),
            parse_rational(term.get("p", 1)),
        ))
    lin = parse_vector(body.get("lin", [0] * N), "lin")
    const = parse_rational(body.get("const", 0))

    def g(x):
        total = const + sum((li * xi for li, xi in zip(lin, x)), ZERO)
        for q, r, p in relus:
            pre = sum((qi * xi for qi, xi in zip(q, x)), r)
            if pre > ZERO:
                total += p * pre
        return total

    mismatches = sum(1 for x in fresh_points() if g(x) != f(x))
    if mismatches == 0:
        return reply({"solved": True, "token": TOKEN})
    return reply({"solved": False, "mismatches": mismatches})


if __name__ == "__main__":
    logging.getLogger("werkzeug").setLevel(logging.ERROR)   # no per-request noise
    print("synapse: n=%d H=%d, serving on :80" % (N, H), flush=True)
    app.run(host="0.0.0.0", port=80, threaded=True, debug=False)
