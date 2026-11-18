#!/usr/bin/env python3
"""
resin -- the puzzle service.

The Resin Block: N brass studs on a block of cast resin. Before the pour,
resistors were soldered between some pairs of studs. The service answers one
kind of question -- "what does an ideal ohmmeter read between studs a and b?"
-- and checks a submitted wiring.

Model
  * The wiring is a connected, sparse, simple, undirected graph on the studs
    0 .. N-1. A wire {i, j} has a positive rational weight w_ij: the
    conductance of that resistor (its own resistance is 1 / w_ij).
  * Laplacian  L = D - W   (L_ij = -w_ij off the diagonal, L_ii = sum_j w_ij).
  * Effective resistance  R_ij = L+_ii + L+_jj - 2 L+_ij, where L+ is the
    Moore-Penrose pseudoinverse of L, computed exactly over fractions.Fraction
    as  L+ = (L + J/N)^-1 - J/N  (J = the all-ones matrix).

Endpoints
  GET  /            the manual: n and the endpoints. Never the wiring.
  POST /resistance  {"i": a, "j": b}  ->  {"resistance": "num/den"}
  POST /submit      {"edges": [[i, j, "num/den"], ...]}
                    ->  {"solved": true, "token": "FLAG{...}"}
                     |  {"solved": false}

The wiring and the token are drawn once, at startup, from the OS random
source. From then on every answer is a pure function of the request. Nothing
drawn at startup is ever printed or logged.
"""
import logging
import re
import secrets
from fractions import Fraction

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

# ----------------------------------------------------------------------------
#  Parameters of the draw
# ----------------------------------------------------------------------------
N = 30                              # studs, labelled 0 .. N-1
EXTRA_MIN, EXTRA_MAX = 11, 16       # wires on top of the N-1 of the spanning tree
NUMERATORS = range(1, 10)           # a weight is p/q with p in 1..9
DENOMINATORS = range(1, 7)          #                 and q in 1..6

# ----------------------------------------------------------------------------
#  Limits on what /submit will read
# ----------------------------------------------------------------------------
MAX_BODY = 512 * 1024               # bytes
MAX_EDGES = 4 * (N * (N - 1) // 2)  # list entries (repeats of a pair are allowed)
MAX_DIGITS = 120                    # digits in a numerator or a denominator


# ----------------------------------------------------------------------------
#  Exact linear algebra
# ----------------------------------------------------------------------------
def invert(matrix):
    """Exact inverse of a square Fraction matrix (Gauss-Jordan)."""
    n = len(matrix)
    rows = [list(row) + [Fraction(int(i == j)) for j in range(n)]
            for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = next((r for r in range(col, n) if rows[r][col] != 0), None)
        if pivot is None:
            raise ValueError("singular matrix")
        rows[col], rows[pivot] = rows[pivot], rows[col]
        head = rows[col][col]
        rows[col] = [x / head for x in rows[col]]
        for r in range(n):
            factor = rows[r][col]
            if r != col and factor != 0:
                rows[r] = [x - factor * y for x, y in zip(rows[r], rows[col])]
    return [row[n:] for row in rows]


def laplacian(n, wiring):
    """wiring: {(a, b): weight} with a < b. Returns L = D - W as Fractions."""
    lap = [[Fraction(0)] * n for _ in range(n)]
    for (a, b), w in wiring.items():
        lap[a][b] -= w
        lap[b][a] -= w
        lap[a][a] += w
        lap[b][b] += w
    return lap


def pseudoinverse(lap):
    """Moore-Penrose pseudoinverse of a connected graph's Laplacian.

    L has the single null direction 1, so L + J/n is invertible and
    (L + J/n)^-1 = L+ + J/n.
    """
    n = len(lap)
    u = Fraction(1, n)
    shifted = invert([[lap[i][j] + u for j in range(n)] for i in range(n)])
    return [[shifted[i][j] - u for j in range(n)] for i in range(n)]


def resistance_matrix(pinv):
    """R_ij = L+_ii + L+_jj - 2 L+_ij."""
    n = len(pinv)
    return [[pinv[i][i] + pinv[j][j] - 2 * pinv[i][j] for j in range(n)]
            for i in range(n)]


def check_pseudoinverse(lap, pinv):
    """Refuse to serve unless L+ really is the pseudoinverse (exact identities)."""
    n = len(lap)
    u = Fraction(1, n)
    for i in range(n):
        if sum(pinv[i]) != 0:
            raise RuntimeError("L+ rows must sum to zero")
        for j in range(n):
            if pinv[i][j] != pinv[j][i]:
                raise RuntimeError("L+ must be symmetric")
            entry = sum(lap[i][k] * pinv[k][j] for k in range(n))
            if entry != Fraction(int(i == j)) - u:
                raise RuntimeError("L L+ must equal I - J/n")


# ----------------------------------------------------------------------------
#  The draw
# ----------------------------------------------------------------------------
def draw_wiring(n, rng):
    """A connected sparse graph: a random spanning tree plus a few extra wires."""
    order = list(range(n))
    rng.shuffle(order)
    pairs = set()
    for k in range(1, n):                       # tree: hang each stud on an earlier one
        a, b = order[k], order[rng.randrange(k)]
        pairs.add((min(a, b), max(a, b)))
    target = (n - 1) + rng.randint(EXTRA_MIN, EXTRA_MAX)
    while len(pairs) < target:                  # extras: close a few loops
        a, b = rng.sample(range(n), 2)
        pairs.add((min(a, b), max(a, b)))
    return {pair: Fraction(rng.choice(NUMERATORS), rng.choice(DENOMINATORS))
            for pair in sorted(pairs)}


def reading_hides_wiring(n, wiring, table):
    """True iff no cut-off on the readings separates wired from unwired pairs,
    i.e. some unwired pair reads strictly lower than some wired pair."""
    wired = [table[a][b] for (a, b) in wiring]
    unwired = [table[a][b] for a in range(n) for b in range(a + 1, n)
               if (a, b) not in wiring]
    return min(unwired) < max(wired)


class Block:
    """One drawn instance: the wiring, its Laplacian and the exact readings."""

    def __init__(self, n, rng):
        while True:
            self.wiring = draw_wiring(n, rng)
            self.laplacian = laplacian(n, self.wiring)
            pinv = pseudoinverse(self.laplacian)
            check_pseudoinverse(self.laplacian, pinv)
            table = resistance_matrix(pinv)
            if reading_hides_wiring(n, self.wiring, table):
                break
        self.n = n
        self.readings = [["%d/%d" % (x.numerator, x.denominator) for x in row]
                         for row in table]

    def same_wiring(self, totals):
        """Exact Laplacian equality, scanning every entry (no early exit)."""
        mine = laplacian(self.n, totals)
        differing = 0
        for i in range(self.n):
            for j in range(self.n):
                differing += mine[i][j] != self.laplacian[i][j]
        return differing == 0


_rng = secrets.SystemRandom()
BLOCK = Block(N, _rng)
TOKEN = "FLAG{" + secrets.token_hex(16) + "}"
INSTANCE = secrets.token_hex(4)     # public; changes whenever the wiring is redrawn


# ----------------------------------------------------------------------------
#  HTTP
# ----------------------------------------------------------------------------
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_BODY
app.json.sort_keys = False

RESISTANCE_USAGE = ('send JSON like {"i": a, "j": b} with a and b integers in 0 .. %d'
                    % (N - 1))
SUBMIT_USAGE = ('send JSON like {"edges": [[i, j, "num/den"], ...]}: i and j are '
                'different integers in 0 .. %d, the weight is an exact fraction '
                'such as "7/3" (or an integer)' % (N - 1))

_WEIGHT = re.compile(r"[+-]?\d{1,%d}(/\d{1,%d})?" % (MAX_DIGITS, MAX_DIGITS))


def describe():
    return {
        "name": "resin",
        "about": ("The Resin Block. %d brass studs stick out of a block of cast "
                  "resin. Before the pour, resistors were soldered between some "
                  "pairs of studs. The resin is opaque. An ideal ohmmeter is "
                  "clipped to the bench." % N),
        "n": N,
        "nodes": "the studs are labelled 0 .. %d" % (N - 1),
        "instance": INSTANCE,
        "network": {
            "shape": ("a connected, sparse, undirected graph on the studs: at "
                      "most one wire per pair, no wire from a stud to itself"),
            "weights": ("each wire {i, j} has a positive rational weight w: the "
                        "conductance of that resistor (its own resistance is 1/w)"),
            "drawn": ("fresh every time the service starts; `instance` changes "
                      "when it does"),
        },
        "numbers": ("every number is an exact fraction in lowest terms, written "
                    '"num/den" with den >= 1 (an integer k is "k/1")'),
        "endpoints": {
            "GET /": "this manual",
            "POST /resistance": {
                "body": {"i": "a", "j": "b"},
                "returns": {"resistance": "num/den"},
                "meaning": ("the effective resistance between studs a and b: the "
                            "voltage between them when one unit of current is "
                            "fed in at a and drawn out at b, with the whole "
                            "network in place. Exact. Symmetric in a and b; "
                            '"0/1" when a = b.'),
            },
            "POST /submit": {
                "body": {"edges": [["i", "j", "w_num/w_den"], "..."]},
                "returns": [{"solved": True, "token": "FLAG{...}"},
                            {"solved": False}],
                "rule": ("order and orientation do not matter, and weights "
                         "listed for the same pair are added. Solved iff, pair "
                         "by pair, your totals equal the hidden weights exactly "
                         "(and are zero wherever there is no wire)."),
            },
        },
        "goal": "POST /submit the wiring of the block, weights included.",
        "limits": {
            "rate": "none",
            "submit": ("at most %d list entries and %d bytes; at most %d digits "
                       "in a numerator or denominator"
                       % (MAX_EDGES, MAX_BODY, MAX_DIGITS)),
        },
    }


def bad(message, code=400):
    return jsonify({"error": message}), code


def stud(value):
    """A stud label, or None."""
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if 0 <= value < N else None


def weight(value):
    """An exact rational from "num/den", "k" or a JSON integer, or None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return Fraction(value) if abs(value) < 10 ** MAX_DIGITS else None
    if isinstance(value, str) and _WEIGHT.fullmatch(value.strip()):
        try:
            return Fraction(value.strip())
        except (ValueError, ZeroDivisionError):
            return None
    return None


@app.get("/")
def manual():
    return jsonify(describe())


@app.post("/resistance")
def resistance():
    body = request.get_json(force=True, silent=True)
    if not isinstance(body, dict):
        return bad(RESISTANCE_USAGE)
    a, b = stud(body.get("i")), stud(body.get("j"))
    if a is None or b is None:
        return bad(RESISTANCE_USAGE)
    return jsonify({"resistance": BLOCK.readings[a][b]})


@app.post("/submit")
def submit():
    body = request.get_json(force=True, silent=True)
    if not isinstance(body, dict) or not isinstance(body.get("edges"), list):
        return bad(SUBMIT_USAGE)
    edges = body["edges"]
    if len(edges) > MAX_EDGES:
        return bad("too many entries: at most %d" % MAX_EDGES)
    totals = {}
    for k, entry in enumerate(edges):
        if not isinstance(entry, list) or len(entry) != 3:
            return bad("edges[%d] is not [i, j, weight]. %s" % (k, SUBMIT_USAGE))
        a, b, w = stud(entry[0]), stud(entry[1]), weight(entry[2])
        if a is None or b is None or a == b:
            return bad("edges[%d] has bad stud labels. %s" % (k, SUBMIT_USAGE))
        if w is None:
            return bad("edges[%d] has a bad weight. %s" % (k, SUBMIT_USAGE))
        pair = (min(a, b), max(a, b))
        totals[pair] = totals.get(pair, Fraction(0)) + w
    if BLOCK.same_wiring(totals):
        return jsonify({"solved": True, "token": TOKEN})
    return jsonify({"solved": False})


@app.errorhandler(HTTPException)
def http_error(err):
    return bad("%d %s; see GET /" % (err.code, err.name), err.code)


if __name__ == "__main__":
    # Keep the logs quiet and secret-free: no per-request lines, and nothing
    # drawn at startup is printed.
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    print("resin: block cast, %d studs, serving on :80" % N, flush=True)
    app.run(host="0.0.0.0", port=80, threaded=True)
