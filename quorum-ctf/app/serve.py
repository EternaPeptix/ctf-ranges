#!/usr/bin/env python3
"""
quorum -- puzzle service.

A bench of M = 250 witnesses guards one sealed positive integer N < B = 2^2000.
Witness i holds a distinct 20-bit prime p_i and, when asked, states N mod p_i.
At most 70 witnesses are liars: a liar states one fixed wrong remainder, the
same on every query. Whoever submits N gets the completion token.

  GET  /          the rules: primes p_0..p_{M-1}, the bound B, max_liars, endpoints
  POST /residue   {"i": <index>}             -> {"residue": <integer>}
  POST /submit    {"N": "<decimal integer>"} -> {"solved": true, "token": "FLAG{...}"}
                                                or {"solved": false}

Everything secret (N, which witnesses lie, their false remainders, the token)
is drawn from the operating system's random source at start, lives only in
memory, and is never logged. The primes are drawn at start too, and are public.

Before listening, the service checks that the draw is decodable in the worst
case, whichever witnesses lie:

    2 * B * Emax^2 < Mprod      Mprod = p_0 * ... * p_{M-1}
                                Emax  = product of the MAX_LIARS largest primes

With the constants below that can never fail: Mprod = Emax * (product of the
180 smallest primes), so the inequality is 2 * B * Emax < that product, and
2 * 2^2000 * (2^20)^70 = 2^3401 < 2^3420 = (2^19)^180. The check is still made
on the actual draw, and the process exits rather than serve a box that fails it
(which is what would happen if the constants were edited carelessly).

Flask + standard library only.
"""
import hmac
import json
import logging
import math
import secrets
import sys

from flask import Flask, Response, jsonify, request
from werkzeug.exceptions import HTTPException

M = 250                    # witnesses = moduli
PRIME_BITS = 20            # every p_i lies in [2^19, 2^20)
N_BITS = 2000              # N is drawn with exactly this many bits
BOUND = 1 << N_BITS        # the public bound: 0 < N < BOUND
MAX_LIARS = 70             # the public promise: at most this many liars
LIARS = MAX_LIARS          # how many this service actually marks (the worst case)
MAX_BODY = 16 * 1024       # request bodies are tiny
MAX_DIGITS = 700           # BOUND has 603 decimal digits

RNG = secrets.SystemRandom()
STATE = {}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_BODY


# --------------------------------------------------------------------------
#  Number theory
# --------------------------------------------------------------------------
def is_prime(n):
    """Miller-Rabin to bases 2, 3, 5, 7: exact for every n < 3,215,031,751."""
    if n < 2:
        return False
    for q in (2, 3, 5, 7, 11, 13):
        if n % q == 0:
            return n == q
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for a in (2, 3, 5, 7):
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


def draw_primes():
    """M distinct random primes of exactly PRIME_BITS bits, ascending."""
    lo, hi = 1 << (PRIME_BITS - 1), 1 << PRIME_BITS
    found = set()
    while len(found) < M:
        candidate = RNG.randrange(lo, hi) | 1
        if is_prime(candidate):
            found.add(candidate)
    return sorted(found)


def recovery_check(primes):
    """Is 2 * B * Emax^2 < Mprod?  Returns (holds, bits of lhs, bits of Mprod).

    Emax is the product of the MAX_LIARS largest primes, so the inequality
    covers every possible choice of liars, not just the one drawn here.
    """
    mprod = math.prod(primes)
    emax = math.prod(sorted(primes)[-MAX_LIARS:])
    lhs = 2 * BOUND * emax * emax
    return lhs < mprod, lhs.bit_length(), mprod.bit_length()


# --------------------------------------------------------------------------
#  Boot
# --------------------------------------------------------------------------
def audit(primes, n, liars, answers):
    """Refuse to serve a box that does not match its own rules."""
    lo, hi = 1 << (PRIME_BITS - 1), 1 << PRIME_BITS
    assert len(primes) == M == len(set(primes)) == len(answers)
    assert all(lo <= p < hi and is_prime(p) for p in primes)
    assert 0 < n < BOUND and n.bit_length() == N_BITS
    assert len(liars) == LIARS <= MAX_LIARS and all(0 <= i < M for i in liars)
    for i, (p, r) in enumerate(zip(primes, answers)):
        assert 0 <= r < p
        assert (r != n % p) == (i in liars)
    assert recovery_check(primes)[0]


def boot():
    primes = draw_primes()
    holds, lhs_bits, mprod_bits = recovery_check(primes)
    if not holds:
        sys.exit(f"[quorum] refusing to start: 2*B*Emax^2 ({lhs_bits} bits) is not "
                 f"below Mprod ({mprod_bits} bits), recovery would not be guaranteed")

    n = RNG.randrange(BOUND >> 1, BOUND)
    liars = frozenset(RNG.sample(range(M), LIARS))
    answers = []
    for i, p in enumerate(primes):
        truth = n % p
        # A liar's remainder is uniform over the p - 1 wrong values, fixed for good.
        answers.append((truth + RNG.randrange(1, p)) % p if i in liars else truth)
    audit(primes, n, liars, answers)

    width = (N_BITS + 7) // 8
    rules = {
        "name": "quorum",
        "about": (
            f"A bench of {M} witnesses guards one sealed positive integer N. "
            f"Witness i holds the prime primes[i] and, asked through POST /residue, "
            f"states N mod primes[i]. At most {MAX_LIARS} of the witnesses are liars: "
            f"a liar states one fixed wrong remainder, the same on every query. "
            f"Which witnesses lie is not published. 0 < N < bound = 2^{N_BITS}. "
            f"Submit N to POST /submit for the completion token."
        ),
        "M": M,
        "prime_bits": PRIME_BITS,
        "bound_bits": N_BITS,
        "bound": str(BOUND),
        "max_liars": MAX_LIARS,
        "endpoints": {
            "GET /": "these rules",
            "POST /residue": 'body {"i": <index 0..M-1>} -> {"residue": <integer>}: '
                             "witness i's statement of N mod primes[i]",
            "POST /submit": 'body {"N": "<decimal integer>"} -> '
                            '{"solved": true, "token": "FLAG{...}"} if it is N, '
                            'else {"solved": false}',
        },
        "primes": primes,
    }
    STATE.update(
        primes=primes,
        answers=answers,
        width=width,
        n_bytes=n.to_bytes(width, "big"),
        token="FLAG{quorum_" + secrets.token_hex(16) + "}",
        rules=json.dumps(rules).encode(),
    )
    print(f"[quorum] {M} distinct {PRIME_BITS}-bit primes, N has {N_BITS} bits, "
          f"at most {MAX_LIARS} liars", flush=True)
    print(f"[quorum] recovery inequality holds: 2*B*Emax^2 has {lhs_bits} bits, "
          f"Mprod has {mprod_bits} bits", flush=True)


# --------------------------------------------------------------------------
#  HTTP
# --------------------------------------------------------------------------
def parse_integer(value):
    """A non-negative integer from a JSON integer or a string of decimal digits."""
    if isinstance(value, bool):
        raise ValueError("N must be an integer, not a boolean")
    if isinstance(value, int):
        if value < 0:
            raise ValueError("N must not be negative")
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text.isascii() or not text.isdigit():
            raise ValueError("N must be a string of decimal digits")
        if len(text) > MAX_DIGITS:
            raise ValueError("N has too many digits")
        return int(text)
    raise ValueError("N must be a decimal string")


def is_secret(guess):
    if not 0 < guess < BOUND:
        return False
    return hmac.compare_digest(guess.to_bytes(STATE["width"], "big"), STATE["n_bytes"])


@app.errorhandler(HTTPException)
def _http_error(err):
    return jsonify({"error": f"{err.code} {err.name}"}), err.code


@app.get("/")
def rules():
    return Response(STATE["rules"], mimetype="application/json")


@app.post("/residue")
def residue():
    body = request.get_json(silent=True, force=True)
    i = body.get("i") if isinstance(body, dict) else None
    if not isinstance(i, int) or isinstance(i, bool) or not 0 <= i < M:
        return jsonify({"error": f'send JSON {{"i": <integer index 0..{M - 1}>}}'}), 400
    return jsonify({"residue": STATE["answers"][i]})


@app.post("/submit")
def submit():
    body = request.get_json(silent=True, force=True)
    if not isinstance(body, dict) or "N" not in body:
        return jsonify({"solved": False,
                        "error": 'send JSON {"N": "<decimal integer>"}'}), 400
    try:
        guess = parse_integer(body["N"])
    except ValueError as err:
        return jsonify({"solved": False, "error": str(err)}), 400
    if is_secret(guess):
        return jsonify({"solved": True, "token": STATE["token"]})
    return jsonify({"solved": False})


if __name__ == "__main__":
    logging.getLogger("werkzeug").setLevel(logging.WARNING)   # no per-request lines
    boot()
    print("[quorum] the bench is seated; listening on :80", flush=True)
    app.run(host="0.0.0.0", port=80, threaded=True)
