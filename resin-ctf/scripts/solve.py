#!/usr/bin/env python3
"""
resin -- reference solver.

  1. GET /  ->  n.
  2. POST /resistance for every pair i < j (C(n,2) readings): the symmetric,
     zero-diagonal resistance matrix R, as exact Fractions.
  3. Effective resistance is a squared Euclidean distance in the geometry of
     the Laplacian pseudoinverse:  R_ij = L+_ii + L+_jj - 2 L+_ij.  So R is a
     distance matrix, and Fiedler's bordered inverse gives the Laplacian back:

            [ R    1 ] -1      [ -L/2   y ]
            [ 1^T  0 ]     =   [  y^T   z ]

     One Gauss-Jordan elimination of that (n+1) x (n+1) matrix over Fraction.
  4. L = -2 * (top-left n x n block). Off the diagonal L_ij = -weight(i, j),
     and because the arithmetic is exact, every unwired pair comes out as an
     exact 0. Read off the wires and their weights.
  5. POST /submit, print  TOKEN: <token>.

Nothing here knows anything about the wiring in advance; it uses the same
three endpoints a player has.

Standard library only. Override the target with RESIN_URL
(e.g. http://localhost:9600 from the host).
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from fractions import Fraction

BASE = os.environ.get("RESIN_URL", "http://app").rstrip("/")
ROUNDS = 3      # full restarts allowed if the block is recast under our feet


def say(msg):
    print("[solve] " + msg, flush=True)


def call(path, body=None, tries=8, pause=0.25):
    """One JSON request. Every endpoint is pure, so retrying is safe."""
    data = None if body is None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json"} if data else {}
    last = None
    for attempt in range(1, tries + 1):
        try:
            req = urllib.request.Request(BASE + path, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise SystemExit("HTTP %d from %s: %s" % (exc.code, path, detail))
        except (urllib.error.URLError, OSError, ValueError) as exc:
            last = exc
            time.sleep(pause * attempt)
    raise SystemExit("no answer from %s%s: %s" % (BASE, path, last))


def wait_for_service(seconds=90):
    """The service may still be starting right after `make up` / `make reset`."""
    deadline = time.time() + seconds
    while True:
        try:
            with urllib.request.urlopen(BASE + "/", timeout=5) as resp:
                return json.loads(resp.read().decode())
        except (urllib.error.URLError, OSError, ValueError) as exc:
            if time.time() > deadline:
                raise SystemExit("service at %s never came up: %s" % (BASE, exc))
            time.sleep(0.5)


# ----------------------------------------------------------------------------
#  Step 2: all the readings
# ----------------------------------------------------------------------------
def measure(n):
    """The full resistance matrix, one query per unordered pair."""
    table = [[Fraction(0)] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            reading = call("/resistance", {"i": i, "j": j})["resistance"]
            table[i][j] = table[j][i] = Fraction(reading)
    return table


# ----------------------------------------------------------------------------
#  Step 3: one exact elimination
# ----------------------------------------------------------------------------
def invert(matrix):
    """Exact inverse of a square Fraction matrix (Gauss-Jordan).

    The pivot search matters here: the bordered matrix has a zero diagonal.
    """
    n = len(matrix)
    rows = [list(row) + [Fraction(int(i == j)) for j in range(n)]
            for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = next((r for r in range(col, n) if rows[r][col] != 0), None)
        if pivot is None:
            raise SystemExit("bordered matrix is singular: readings are not "
                             "those of a connected network")
        rows[col], rows[pivot] = rows[pivot], rows[col]
        head = rows[col][col]
        rows[col] = [x / head for x in rows[col]]
        for r in range(n):
            factor = rows[r][col]
            if r != col and factor != 0:
                rows[r] = [x - factor * y for x, y in zip(rows[r], rows[col])]
    return [row[n:] for row in rows]


def laplacian_from_readings(table):
    """Fiedler: the n x n block of [[R, 1], [1^T, 0]]^-1 is -L/2."""
    n = len(table)
    one = Fraction(1)
    bordered = [list(table[i]) + [one] for i in range(n)]
    bordered.append([one] * n + [Fraction(0)])
    inverse = invert(bordered)
    return [[-2 * inverse[i][j] for j in range(n)] for i in range(n)]


# ----------------------------------------------------------------------------
#  Step 4: read the wiring off the Laplacian
# ----------------------------------------------------------------------------
def wiring_from_laplacian(lap):
    """[(i, j, weight)] for i < j, after checking that `lap` is a Laplacian."""
    n = len(lap)
    wires = []
    for i in range(n):
        if sum(lap[i]) != 0:
            raise SystemExit("row %d of the recovered matrix does not sum to 0" % i)
        for j in range(i + 1, n):
            if lap[i][j] != lap[j][i]:
                raise SystemExit("recovered matrix is not symmetric at %d,%d" % (i, j))
            if lap[i][j] > 0:
                raise SystemExit("negative weight on pair %d,%d" % (i, j))
            if lap[i][j] != 0:
                wires.append((i, j, -lap[i][j]))
    return wires


def connected(n, wires):
    neighbours = {v: [] for v in range(n)}
    for i, j, _ in wires:
        neighbours[i].append(j)
        neighbours[j].append(i)
    seen, stack = {0}, [0]
    while stack:
        for nxt in neighbours[stack.pop()]:
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return len(seen) == n


def show(fraction):
    return "%d/%d" % (fraction.numerator, fraction.denominator)


# ----------------------------------------------------------------------------
def attempt(doc):
    """One full pass. Returns the token, or None if the block changed mid-run."""
    n, instance = doc["n"], doc.get("instance")
    pairs = n * (n - 1) // 2
    say("target %s: n = %d studs, instance %s" % (BASE, n, instance))

    started = time.time()
    table = measure(n)
    widest = max(len(str(x.denominator)) for row in table for x in row)
    say("measured all %d pairs in %.1fs (denominators up to %d digits)"
        % (pairs, time.time() - started, widest))

    started = time.time()
    lap = laplacian_from_readings(table)
    say("inverted the %dx%d bordered matrix over Fraction in %.1fs"
        % (n + 1, n + 1, time.time() - started))

    wires = wiring_from_laplacian(lap)
    if not connected(n, wires):
        raise SystemExit("recovered wiring is not connected")
    say("Laplacian recovered: %d wires, %d pairs are exact zeros"
        % (len(wires), pairs - len(wires)))
    say("weights range from %s to %s; the wiring is connected, with %d loops"
        % (show(min(w for _, _, w in wires)), show(max(w for _, _, w in wires)),
           len(wires) - (n - 1)))

    wired = {(i, j) for i, j, _ in wires}
    low = min(table[i][j] for i in range(n) for j in range(i + 1, n)
              if (i, j) not in wired)
    high = max(table[i][j] for i, j in wired)
    say("lowest reading on an unwired pair %.4f, highest on a wired pair %.4f"
        % (float(low), float(high)))

    if call("/").get("instance") != instance:
        say("the block was recast while measuring; starting over")
        return None
    answer = call("/submit", {"edges": [[i, j, show(w)] for i, j, w in wires]})
    if answer.get("solved") and answer.get("token"):
        say("submitted %d wires: solved" % len(wires))
        return answer["token"]
    say("submitted %d wires: not accepted" % len(wires))
    return None


def main():
    doc = wait_for_service()
    for _ in range(ROUNDS):
        token = attempt(doc)
        if token:
            print("TOKEN: " + token, flush=True)
            return 0
        doc = wait_for_service()
    say("gave up after %d rounds" % ROUNDS)
    return 1


if __name__ == "__main__":
    sys.exit(main())
