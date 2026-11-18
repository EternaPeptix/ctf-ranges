#!/usr/bin/env python3
"""
quorum -- reference solver.

Chinese remaindering with errors, decoded by rational reconstruction (the
integer form of Berlekamp-Welch).

  1. GET /             primes p_0..p_{M-1}, the bound B, max_liars
  2. POST /residue     r_i for every i (some of them lies)
  3. CRT               R with R = r_i (mod p_i) and 0 <= R < Mprod = prod p_i.
                       On its own R is garbage: the lies are folded into it.
  4. Let E = product of the liar primes (unknown). Then
                           E * R = E * N   (mod Mprod)
                       because R = N modulo every honest prime and E = 0 modulo
                       every liar prime. Both E and E*N are small next to Mprod,
                       so (a, b) = (E*N, E) is the row of the extended Euclidean
                       algorithm on (Mprod, R) at which the remainder first
                       drops below B * Emax, with Emax = product of the
                       max_liars largest primes. Guaranteed whenever
                           2 * B * Emax^2 < Mprod.
  5. N = a / b         checked against the residues: at most max_liars
                       disagree, and b is exactly the product of their primes.
  6. POST /submit      {"N": str(N)}  ->  the completion token

Standard library only. No randomness, no search: a run is a pure function of
the box. Override the target with QUORUM_URL (e.g. http://localhost:9400 from
the host).
"""
import http.client
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request

BASE = os.environ.get("QUORUM_URL", "http://app").rstrip("/")
BOOT_WAIT = 120            # seconds to wait for the service to come up


def say(msg):
    print(msg, flush=True)


# --------------------------------------------------------------------------
#  HTTP
# --------------------------------------------------------------------------
def call(path, payload=None, timeout=15):
    """GET (payload is None) or POST JSON. Returns the decoded JSON body."""
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(BASE + path, data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", "replace")[:200]
        raise RuntimeError(f"{path}: HTTP {err.code}: {body}") from None


def fetch_rules():
    """GET /, retrying while the service is still coming up."""
    deadline = time.time() + BOOT_WAIT
    while True:
        try:
            return call("/")
        except (OSError, http.client.HTTPException, ValueError, RuntimeError) as err:
            if time.time() > deadline:
                raise RuntimeError(f"no rules from {BASE} after {BOOT_WAIT}s: {err}")
            time.sleep(0.5)


# --------------------------------------------------------------------------
#  Number theory
# --------------------------------------------------------------------------
def crt(residues, primes):
    """(R, m) with R = r_i (mod p_i) for every i and 0 <= R < m = prod p_i."""
    R, m = 0, 1
    for r, p in zip(residues, primes):
        R += m * ((r - R) * pow(m, -1, p) % p)
        m *= p
    return R, m


def reconstruct(R, m, cap):
    """Extended Euclid on (m, R), stopped at the first remainder below cap.

    Every row (a, b) satisfies a = b * R (mod m); the remainders a fall while
    the cofactors |b| grow. Returns the stopping row as (a, |b|).
    """
    a0, b0, a1, b1 = m, 0, R, 1
    while a1 >= cap:
        q = a0 // a1
        a0, b0, a1, b1 = a1, b1, a0 - q * a1, b0 - q * b1
    return a1, abs(b1)


# --------------------------------------------------------------------------
#  The solve
# --------------------------------------------------------------------------
def main():
    box = fetch_rules()
    primes = [int(p) for p in box["primes"]]
    bound, max_liars = int(box["bound"]), int(box["max_liars"])
    say(f"[solve] rules at {BASE}: {len(primes)} primes of "
        f"{min(primes).bit_length()}..{max(primes).bit_length()} bits, "
        f"N < 2^{bound.bit_length() - 1}, at most {max_liars} liars")

    # 2. Every witness's statement.
    t0 = time.perf_counter()
    residues = [int(call("/residue", {"i": i})["residue"]) for i in range(len(primes))]
    say(f"[solve] {len(residues)} residues collected in {time.perf_counter() - t0:.2f} s")

    # 3. Plain CRT over everything.
    R, mprod = crt(residues, primes)
    say(f"[solve] plain CRT: R has {R.bit_length()} bits modulo a {mprod.bit_length()}-bit "
        f"product -- not N, the lies are folded in")

    # 4. Rational reconstruction, with the worst-case guarantee checked first.
    emax = math.prod(sorted(primes)[-max_liars:])
    lhs = 2 * bound * emax * emax
    if lhs >= mprod:
        raise RuntimeError("2*B*Emax^2 < Mprod does not hold; recovery is not guaranteed")
    say(f"[solve] 2*B*Emax^2 has {lhs.bit_length()} bits < Mprod with {mprod.bit_length()} "
        f"bits: recovery is guaranteed")
    a, b = reconstruct(R, mprod, bound * emax)

    # 5. N = a / b, and the liars fall out with it.
    if b == 0 or a % b:
        raise RuntimeError("reconstructed pair (a, b) is not an integer ratio")
    n = a // b
    liars = [i for i, (p, r) in enumerate(zip(primes, residues)) if n % p != r]
    if not 0 < n < bound or len(liars) > max_liars:
        raise RuntimeError(f"candidate N fails the check ({len(liars)} residues disagree)")
    if math.prod(primes[i] for i in liars) != b:
        raise RuntimeError("b is not the product of the disagreeing primes")
    say(f"[solve] a/b with b of {b.bit_length()} bits gives N of {n.bit_length()} bits; "
        f"{len(primes) - len(liars)} residues agree, {len(liars)} witnesses lied, "
        f"and b is exactly the product of their primes")

    # 6. Submit.
    verdict = call("/submit", {"N": str(n)})
    if verdict.get("solved") is not True or "token" not in verdict:
        raise RuntimeError(f"/submit refused the recovered N: {verdict}")
    say("[solve] /submit accepted N")
    say(f"TOKEN: {verdict['token']}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, KeyError, TypeError, ValueError) as err:
        say(f"[solve] FAILED: {type(err).__name__}: {err}")
        sys.exit(1)
