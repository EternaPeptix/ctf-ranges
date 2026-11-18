#!/usr/bin/env python3
"""orrery -- a sparse-polynomial reconstruction puzzle.

A brass orrery with six arms.  Behind the dial plate sits a hidden gear train:
a sparse polynomial f in six variables over the prime field F_p.

    GET  /        describes p, the bounds, the budget and the endpoints
    POST /eval    {"x": [v0..v5]}                 -> {"y": f(x) mod p}   (costs 1 of 32)
    POST /submit  {"terms": [[e0..e5, coeff]..]}  -> {"solved": true, "token": "FLAG{...}"}
                                                     or {"solved": false}

f and the token are drawn from the OS random source at startup and live only in
this process's memory.  Nothing here ever prints, logs or returns the terms.
"""
import logging
import secrets
import threading

from flask import Flask, jsonify, request

P = 2**300 + 157        # fixed 301-bit prime (the first prime above 2^300)
NVARS = 6               # variables x0..x5 (the six arms)
MAX_DEG = 20            # every exponent is in 0..MAX_DEG
MAX_TERMS = 16          # documented bound on the number of terms
MIN_TERMS = 8           # undocumented floor, so no instance is degenerate
BUDGET = 32             # successful /eval calls per startup
MAX_SUBMIT_TERMS = 256  # sanity cap on a submission's length


def is_probable_prime(n):
    d, s = n - 1, 0
    while d % 2 == 0:
        d, s = d // 2, s + 1
    for a in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53):
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


# p must be prime, and larger than any monomial evaluated at small integers
# (see organizer/SOLUTION.md for why that matters).
assert is_probable_prime(P) and P > (2 * 3 * 5 * 7 * 11 * 13) ** MAX_DEG


def draw_polynomial():
    """{exponent tuple: nonzero coefficient}: MIN_TERMS..MAX_TERMS distinct monomials."""
    rng = secrets.SystemRandom()
    count = rng.randint(MIN_TERMS, MAX_TERMS)
    poly = {}
    while len(poly) < count:
        expo = tuple(rng.randint(0, MAX_DEG) for _ in range(NVARS))
        poly.setdefault(expo, rng.randrange(1, P))
    return poly


POLY = draw_polynomial()
TOKEN = "FLAG{" + secrets.token_hex(16) + "}"

_lock = threading.Lock()
_used = 0               # successful /eval calls so far

app = Flask(__name__)
app.json.sort_keys = False
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024


def evaluate(x):
    total = 0
    for expo, coeff in POLY.items():
        term = coeff
        for v, e in zip(x, expo):
            term = term * pow(v, e, P) % P
        total += term
    return total % P


def canonical(terms):
    """A submitted term list as {exponent tuple: nonzero coeff mod p}; None if malformed.

    Like terms are combined and zero coefficients dropped, so the comparison with
    POLY is equality of polynomials, not of spellings.
    """
    if not isinstance(terms, list) or len(terms) > MAX_SUBMIT_TERMS:
        return None
    poly = {}
    for term in terms:
        if not isinstance(term, list) or len(term) != NVARS + 1:
            return None
        if any(type(v) is not int for v in term) or min(term[:NVARS]) < 0:
            return None
        expo = tuple(term[:NVARS])
        poly[expo] = (poly.get(expo, 0) + term[NVARS]) % P
    return {expo: coeff for expo, coeff in poly.items() if coeff}


def json_body():
    try:
        data = request.get_json(force=True, silent=True)
    except Exception:       # oversized or pathological bodies
        return None
    return data if isinstance(data, dict) else None


@app.get("/")
def index():
    with _lock:
        used = _used
    return jsonify({
        "name": "orrery",
        "about": (
            "A brass orrery with six arms. Behind the dial plate a hidden gear train "
            "computes y = f(x0,...,x5) mod p, where f is a sparse polynomial. Set the "
            "arms, read the pointer, and tell the orrery its own gear train."
        ),
        "p": P,
        "p_bits": P.bit_length(),
        "variables": NVARS,
        "max_degree_per_variable": MAX_DEG,
        "max_terms": MAX_TERMS,
        "budget": {"evaluations": BUDGET, "used": used, "remaining": BUDGET - used},
        "endpoints": {
            "GET /": "this description",
            "POST /eval": {
                "body": {"x": ["v0", "v1", "v2", "v3", "v4", "v5"]},
                "returns": {"y": "f(x) mod p"},
                "cost": "one evaluation per answered call",
            },
            "POST /submit": {
                "body": {"terms": [["e0", "e1", "e2", "e3", "e4", "e5", "coeff"]]},
                "returns": {"solved": "true only if the terms are exactly f", "token": "FLAG{...} when solved"},
                "cost": "free",
            },
        },
        "notes": [
            "f has at most %d terms; each is coeff * x0^e0 * ... * x5^e5 with every exponent in 0..%d."
            % (MAX_TERMS, MAX_DEG),
            "How many terms there are, which exponents and which coefficients are all secret.",
            "All numbers are plain JSON integers; values and coefficients are taken modulo p.",
            "The budget is per gear train. Rejected (malformed) requests are free; answered /eval calls are not. A correct submission reveals the token and winds a fresh gear train with a full spring.",
        ],
    })


@app.post("/eval")
def eval_point():
    global _used
    data = json_body()
    x = data.get("x") if data else None
    if not (isinstance(x, list) and len(x) == NVARS and all(type(v) is int for v in x)):
        return jsonify(error='body must be {"x": [v0, v1, v2, v3, v4, v5]} with six integers'), 400
    with _lock:
        if _used >= BUDGET:
            return jsonify(error="the mainspring has run down: all %d evaluations are spent" % BUDGET, remaining=0), 429
        _used += 1
        left = BUDGET - _used
    resp = jsonify(y=evaluate(x))
    resp.headers["X-Evaluations-Remaining"] = str(left)
    return resp


@app.post("/submit")
def submit():
    global POLY, _used
    data = json_body()
    guess = canonical(data.get("terms") if data else None)
    if guess is None:
        return jsonify(
            solved=False,
            error='body must be {"terms": [[e0, e1, e2, e3, e4, e5, coeff], ...]} with integer '
                  "entries, exponents >= 0 and at most %d terms" % MAX_SUBMIT_TERMS,
        ), 400
    with _lock:
        solved = guess == POLY
        if solved:
            # That gear train is solved: wind a fresh one and refill the spring,
            # so the organizer self-check can run again without a restart. The
            # token is fixed at startup; no gear train ever gets more than BUDGET
            # evaluations.
            POLY = draw_polynomial()
            _used = 0
    if solved:
        return jsonify(solved=True, token=TOKEN)
    return jsonify(solved=False)


@app.errorhandler(404)
@app.errorhandler(405)
def no_such_endpoint(err):
    return jsonify(error="endpoints: GET /, POST /eval, POST /submit"), err.code


@app.errorhandler(500)
def internal_error(_err):
    return jsonify(error="internal error"), 500


class _DropHealthProbe(logging.Filter):
    """Keep the container healthcheck (GET / from loopback) out of the access log."""

    def filter(self, record):
        msg = record.getMessage()
        return not (msg.startswith("127.0.0.1 ") and '"GET / ' in msg)


if __name__ == "__main__":
    logging.getLogger("werkzeug").addFilter(_DropHealthProbe())
    print("[orrery] wound up: %d-bit prime field, %d evaluations in the spring" % (P.bit_length(), BUDGET), flush=True)
    app.run(host="0.0.0.0", port=80, threaded=True)
