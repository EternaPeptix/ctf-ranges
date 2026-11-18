#!/usr/bin/env python3
"""
Counterpoise -- reference solver.  Pure standard library, non-adaptive, exact.

All 255 weighings are designed before the first one is made: they are the rows
of the Cantor-Mills detecting matrix D_8 (255 rows x 1024 columns, entries in
{-1, 0, +1}).  Row i becomes one POST /weigh with plus = its +1 columns and
minus = its -1 columns.  The 255 readings m = D_8 . x are then unwound by the
same recursion that built the matrix, which returns x exactly.  No randomness,
no search, no question depends on an earlier answer.

Talks to the service the way a player does: GET /, POST /weigh, POST /submit.
Prints `TOKEN: <token>` and exits 0 on success.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = os.environ.get("COUNTERPOISE_URL", "http://app").rstrip("/")
K = 8  # D_K has 2^K - 1 = 255 rows and K * 2^(K-1) = 1024 columns


# ---------------------------------------------------------------- the method
def detecting(k):
    """D_1 = [1];  D_{j+1} = [[D, D, I, 0], [D, -D, 0, 0], [0, 0, 0, 1]]."""
    D = [[1]]
    for _ in range(k - 1):
        r, c = len(D), len(D[0])
        top = [row + row + [int(i == j) for j in range(r)] + [0] for i, row in enumerate(D)]
        mid = [row + [-v for v in row] + [0] * (r + 1) for row in D]
        D = top + mid + [[0] * (2 * c + r) + [1]]
    return D


def decode(m, k):
    """Invert m = D_k . v for a 0/1 vector v, split as v = (x, y, z, w)."""
    if k == 1:
        return [m[0]]
    r = 2 ** (k - 1) - 1
    a, b = m[:r], m[r:2 * r]                    # a = Dx + Dy + z,  b = Dx - Dy
    z = [(p - q) % 2 for p, q in zip(a, b)]     # a - b = 2*Dy + z  ->  z by parity
    dx = [(p - e + q) // 2 for p, q, e in zip(a, b, z)]
    dy = [(p - e - q) // 2 for p, q, e in zip(a, b, z)]
    return decode(dx, k - 1) + decode(dy, k - 1) + z + [m[2 * r]]


# ------------------------------------------------------------------ plumbing
def call(path, payload=None):
    """One HTTP exchange -> (status, parsed JSON).  GET when payload is None."""
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(BASE + path, data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, json.load(resp)
    except urllib.error.HTTPError as err:
        try:
            return err.code, json.load(err)
        except ValueError:
            return err.code, {}


def say(msg):
    print(msg, flush=True)


def die(msg):
    say("[!] " + msg)
    sys.exit(1)


def wait_for_service(seconds=60):
    """The box may still be booting right after `make up` / `make reset`."""
    deadline = time.time() + seconds
    while True:
        try:
            status, card = call("/")
            if status == 200 and "budget" in card:
                return card
        except (OSError, ValueError):
            pass
        if time.time() > deadline:
            die(f"no answer from {BASE}/ after {seconds}s -- is the box up?  (make up)")
        time.sleep(0.5)


def weigh(question, answered):
    """Ask one question.  A network hiccup is retried only if it was not charged."""
    for _ in range(5):
        try:
            status, out = call("/weigh", question)
        except (OSError, ValueError) as err:
            time.sleep(0.5)
            if wait_for_service()["asked"] != answered:
                die(f"question {answered + 1} was charged but its answer was lost ({err}); "
                    "`make reset` deals a fresh vector")
            continue
        if status != 200:
            die(f"/weigh refused question {answered + 1}: HTTP {status} {out}")
        return out["result"]
    die(f"could not deliver question {answered + 1}")


def main():
    card = wait_for_service()
    n, budget, asked = card["n"], card["budget"], card["asked"]
    say(f"[*] {BASE}: n={n}, budget={budget}, already asked={asked}")

    D = detecting(K)
    say(f"[*] design fixed up front: {len(D)} questions over {len(D[0])} positions")
    if len(D[0]) != n:
        die(f"design covers {len(D[0])} positions but the box hides {n}")
    if budget - asked < len(D):
        die(f"only {budget - asked} questions left on this hidden vector, the design needs "
            f"{len(D)}; `make reset` deals a fresh one")

    readings = []
    for row in D:
        question = {"plus": [j for j, c in enumerate(row) if c > 0],
                    "minus": [j for j, c in enumerate(row) if c < 0]}
        readings.append(weigh(question, asked + len(readings)))
    say(f"[*] asked {len(readings)} questions, all of them before looking at any answer")

    bits = decode(readings, K)
    if any(b not in (0, 1) for b in bits) or any(
            sum(c * b for c, b in zip(row, bits)) != got for row, got in zip(D, readings)):
        die("decoded vector does not reproduce the readings")
    say(f"[*] decoded {len(bits)} bits ({sum(bits)} ones); they reproduce all {len(D)} readings")

    status, out = call("/submit", {"bits": "".join(map(str, bits))})
    if status != 200 or not out.get("solved"):
        die(f"/submit said no: HTTP {status} {out}")
    say(f"TOKEN: {out['token']}")


if __name__ == "__main__":
    main()
