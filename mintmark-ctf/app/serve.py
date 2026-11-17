#!/usr/bin/env python3
"""
mintmark -- a number-theory puzzle box.

The Old Mint keeps a row of coffers in its strongroom. Every coffer is closed
with a lead seal, and every seal was struck between two steel dies. Nobody
outside the die room has ever seen a die. What the strongroom register shows
for a coffer is its mintmark, one large number: the product of the two secret
primes cut into the dies that struck its seal.

Stripped of the lead and the steel:

    directory   V_0 .. V_{N-1}, each the product of two distinct 512-bit primes
    vault       one entry V = V_v (v is public), public exponent e = 65537
    sealed      c = m^e mod V for a secret integer m, 0 < m < V

    GET  /       the register: directory, v, e, c, N, bit sizes, endpoints
    POST /open   {"message": "<decimal or 0x-hex integer>"}
                 -> {"opened": true, "token": "FLAG{...}"} if it is m,
                    {"opened": false} otherwise

How a register is struck (organizer knowledge, see organizer/SOLUTION.md):
2N-1 distinct primes are drawn. Exactly one of them is used twice, once in the
vault and once in one other entry chosen at random. Every other prime goes
into exactly one entry. The register is audited before the service listens.

Everything secret (the primes, the partner entry, m, the token) is drawn from
the operating system's random source at every start and lives in memory only.
Nothing secret is written to disk, the environment, or the logs.
"""
import hmac
import json
import logging
import math
import os
import re
import secrets
import time
from concurrent.futures import ProcessPoolExecutor

from flask import Flask, Response, jsonify, request
from werkzeug.exceptions import HTTPException

N = 128                    # entries in the directory
PRIME_BITS = 512           # every prime is exactly this long
MODULUS_BITS = 2 * PRIME_BITS
E = 65537                  # public exponent (prime)
MR_ROUNDS = 24             # Miller-Rabin rounds per accepted prime
MIN_GAP_BITS = PRIME_BITS - 100   # |p - q| of the vault must be at least this long

MAX_BODY = 16 * 1024       # largest request body /open will read
MAX_MESSAGE_CHARS = 1024   # longest "message" string /open will parse

_rng = secrets.SystemRandom()


# --------------------------------------------------------------------------
#  Primes: Miller-Rabin, standard library only
# --------------------------------------------------------------------------
def _sieve(limit):
    flags = bytearray([1]) * (limit + 1)
    flags[0:2] = b"\x00\x00"
    for i in range(2, math.isqrt(limit) + 1):
        if flags[i]:
            flags[i * i::i] = bytes(len(range(i * i, limit + 1, i)))
    return [i for i, f in enumerate(flags) if f]


SMALL_PRIMES = _sieve(2000)
SMALL_PRIME_SET = frozenset(SMALL_PRIMES)
PRIMORIAL = math.prod(SMALL_PRIMES)      # one gcd replaces 303 trial divisions


def is_probable_prime(n, rounds=MR_ROUNDS):
    """Miller-Rabin with base 2 and then random bases.

    Exact below 1999^2 (the gcd is a complete trial division there). Above
    that a composite survives with probability at most 4^-(rounds - 1) over
    the random bases.
    """
    if n < 2:
        return False
    if n <= SMALL_PRIMES[-1]:
        return n in SMALL_PRIME_SET
    if math.gcd(n, PRIMORIAL) != 1:
        return False
    if n < SMALL_PRIMES[-1] ** 2:
        return True
    d = n - 1
    s = (d & -d).bit_length() - 1        # n - 1 = d * 2^s with d odd
    d >>= s
    for i in range(rounds):
        a = 2 if i == 0 else 2 + secrets.randbelow(n - 3)
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def random_prime(bits=PRIME_BITS):
    """A random prime of exactly `bits` bits that is usable with exponent E.

    The top two bits are set, so the product of any two such primes has
    exactly 2*bits bits. Primes congruent to 1 mod E are skipped, so E is
    invertible modulo (p-1)(q-1) for every pair.
    """
    top = (1 << (bits - 1)) | (1 << (bits - 2)) | 1
    while True:
        n = secrets.randbits(bits) | top
        if n % E != 1 and is_probable_prime(n):
            return n


def _one_prime(_):
    return random_prime()


def draw_primes(count):
    """`count` pairwise distinct primes. Worker processes only save boot time."""
    try:
        workers = len(os.sched_getaffinity(0))
    except AttributeError:
        workers = os.cpu_count() or 1
    workers = max(1, min(workers, 8))
    pool = set()
    if workers > 1:
        try:
            with ProcessPoolExecutor(workers) as ex:
                pool.update(ex.map(_one_prime, range(count), chunksize=2))
        except Exception as err:         # no fork, no semaphores: go serial
            print(f"[mintmark] worker pool unavailable ({type(err).__name__}), "
                  "drawing primes serially", flush=True)
    while len(pool) < count:             # tops up after a (2^-500) repeat too
        pool.add(random_prime())
    return pool


# --------------------------------------------------------------------------
#  The register
# --------------------------------------------------------------------------
class Register:
    """One complete puzzle instance. Only `public()` ever leaves the process."""

    def __init__(self, pairs, v, partner, shared, m):
        self.pairs = pairs                               # [(prime, prime)] per entry
        self.directory = [a * b for a, b in pairs]
        self.v = v                                       # public: the vault's index
        self.partner = partner                           # secret
        self.shared = shared                             # secret
        self.vault = self.directory[v]
        self.m = m                                       # secret
        self.c = pow(m, E, self.vault)

    def public(self):
        return {
            "name": "mintmark",
            "about": (
                "Strongroom register of the Old Mint. directory[i] is the mintmark "
                "on coffer i: the product of the two secret primes on the dies that "
                "struck its seal. Coffer v is the vault. Its sealed value is "
                "c = m^e mod directory[v]. Recover m and POST it to /open."
            ),
            "N": len(self.directory),
            "bits": {"prime": PRIME_BITS, "composite": MODULUS_BITS},
            "e": E,
            "v": self.v,
            "c": str(self.c),
            "endpoints": {
                "GET /": "this register",
                "POST /open": (
                    'body {"message": "<decimal or 0x-hex integer>"}; answers '
                    '{"opened": true, "token": "FLAG{...}"} if the integer is m, '
                    '{"opened": false} otherwise'
                ),
            },
            "directory": [str(x) for x in self.directory],
        }


def compose_message(v, modulus):
    """The secret m: random padding around a short inscription.

    Laid out like a PKCS#1 v1.5 block (00 02 | nonzero random bytes | 00 |
    text). The two leading bytes keep m below 2^(MODULUS_BITS - 14), which is
    below every modulus this box makes, and the padding carries more than 500
    random bits, so m cannot be guessed and has no short e-th root.
    """
    size = (modulus.bit_length() + 7) // 8
    text = f"Old Mint strongroom, coffer {v:03d}: two seals, one die.".encode("ascii")
    padding = bytes(1 + secrets.randbelow(255) for _ in range(size - 3 - len(text)))
    return int.from_bytes(b"\x00\x02" + padding + b"\x00" + text, "big")


def strike(n=N):
    """Draw a fresh register: exactly one prime shared, by the vault and one other."""
    while True:
        dies = list(draw_primes(2 * n - 1))
        _rng.shuffle(dies)
        v, partner = _rng.sample(range(n), 2)
        shared = dies.pop()
        pairs = [None] * n
        pairs[v] = (shared, dies.pop())
        pairs[partner] = (shared, dies.pop())
        for i in range(n):
            if pairs[i] is None:
                pairs[i] = (dies.pop(), dies.pop())
        assert not dies
        p, q = pairs[v]
        if abs(p - q).bit_length() < MIN_GAP_BITS:       # Fermat-close: redraw
            continue
        reg = Register(pairs, v, partner, shared, compose_message(v, p * q))
        audit(reg)
        return reg


def audit(reg):
    """Every promise the puzzle makes, checked. Raises AssertionError if one fails."""
    n = len(reg.directory)
    V, v, partner, shared = reg.vault, reg.v, reg.partner, reg.shared
    primes = [p for pair in reg.pairs for p in pair]

    # 2n prime slots, 2n-1 distinct primes: one prime is used exactly twice.
    assert v != partner and 0 <= v < n and 0 <= partner < n
    assert len(primes) == 2 * n and len(set(primes)) == 2 * n - 1
    assert primes.count(shared) == 2
    assert shared in reg.pairs[v] and shared in reg.pairs[partner]
    for i, (a, b) in enumerate(reg.pairs):
        assert a != b
        assert a.bit_length() == PRIME_BITS and b.bit_length() == PRIME_BITS
        assert a % E != 1 and b % E != 1
        assert reg.directory[i] == a * b
        assert reg.directory[i].bit_length() == MODULUS_BITS

    # The vault against every other entry: the partner gives the shared prime,
    # everything else gives 1.
    for i in range(n):
        if i == v:
            continue
        g = math.gcd(V, reg.directory[i])
        assert g == (shared if i == partner else 1), f"gcd(V, V_{i}) is wrong"

    # The whole register: no accidental collision anywhere else.
    for i in range(n):
        for j in range(i + 1, n):
            linked = math.gcd(reg.directory[i], reg.directory[j]) != 1
            assert linked == ({i, j} == {v, partner}), f"entries {i} and {j}"

    # The vault is a sound modulus for E and the sealed value is well formed.
    p, q = reg.pairs[v]
    assert math.gcd(E, (p - 1) * (q - 1)) == 1
    assert abs(p - q).bit_length() >= MIN_GAP_BITS
    assert math.gcd(V, PRIMORIAL) == 1
    assert 0 < reg.m < V
    assert reg.c == pow(reg.m, E, V) and 0 < reg.c < V

    # Solve it the way a solver has to, from public values only.
    hits = [(i, g) for i, g in
            ((i, math.gcd(V, x)) for i, x in enumerate(reg.directory) if i != v)
            if 1 < g < V]
    assert hits == [(partner, shared)]
    g = hits[0][1]
    d = pow(E, -1, (g - 1) * (V // g - 1))
    assert pow(reg.c, d, V) == reg.m, "the vault does not open with the recovered key"


# --------------------------------------------------------------------------
#  The service
# --------------------------------------------------------------------------
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_BODY

STATE = {}                 # filled once by boot(), read-only afterwards

_DEC = re.compile(r"[0-9]+\Z")
_HEX = re.compile(r"0[xX][0-9a-fA-F]+\Z")


def boot():
    t0 = time.time()
    reg = strike()
    width = (MODULUS_BITS + 7) // 8
    STATE["vault"] = reg.vault
    STATE["width"] = width
    STATE["m_bytes"] = reg.m.to_bytes(width, "big")
    STATE["token"] = "FLAG{mintmark_two_seals_one_die_" + secrets.token_hex(12) + "}"
    # The register never changes while the service is up: serialise it once.
    STATE["register"] = (json.dumps(reg.public(), indent=1) + "\n").encode("ascii")
    print(f"[mintmark] register struck and audited in {time.time() - t0:.1f}s: "
          f"{len(reg.directory)} coffers, {MODULUS_BITS}-bit mintmarks", flush=True)


def parse_integer(value):
    """A JSON integer, or a string holding a decimal or 0x-hex integer."""
    if isinstance(value, bool):
        raise ValueError("message must be an integer")
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        raise ValueError("message must be a decimal or 0x-hex integer string")
    text = value.strip()
    if len(text) > MAX_MESSAGE_CHARS:
        raise ValueError(f"message longer than {MAX_MESSAGE_CHARS} characters")
    if _HEX.match(text):
        return int(text[2:], 16)
    if _DEC.match(text):
        return int(text)
    raise ValueError("message must be a decimal or 0x-hex integer string")


def is_secret(guess):
    if not 0 < guess < STATE["vault"]:
        return False
    return hmac.compare_digest(guess.to_bytes(STATE["width"], "big"), STATE["m_bytes"])


def _fail(msg, code=400):
    return jsonify({"opened": False, "error": msg}), code


@app.errorhandler(HTTPException)
def _http_error(err):
    return jsonify({"error": f"{err.code} {err.name}"}), err.code


@app.get("/")
def register():
    return Response(STATE["register"], mimetype="application/json")


@app.post("/open")
def open_vault():
    body = request.get_json(silent=True, force=True)
    if not isinstance(body, dict) or "message" not in body:
        return _fail('send JSON {"message": "<decimal or 0x-hex integer>"}')
    try:
        guess = parse_integer(body["message"])
    except ValueError as err:
        return _fail(str(err))
    if is_secret(guess):
        return jsonify({"opened": True, "token": STATE["token"]})
    return jsonify({"opened": False})


if __name__ == "__main__":
    logging.getLogger("werkzeug").setLevel(logging.WARNING)   # no per-request lines
    boot()
    print("[mintmark] strongroom open; listening on :80", flush=True)
    app.run(host="0.0.0.0", port=80, threaded=True)
