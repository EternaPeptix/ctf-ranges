#!/usr/bin/env python3
"""
mintmark -- reference solver.

The vault's number V is a 1024-bit product of two 512-bit primes and cannot be
factored on its own. It does not have to be: one other entry of the directory
was built with one of the same two primes, and the greatest common divisor of
two numbers costs microseconds.

  1. GET /                 directory V_0..V_{N-1}, vault index v, e, c
  2. for every i != v      g = gcd(V, V_i); the one entry with 1 < g < V
                           gives g = p, the shared prime
  3. q = V // p            d = e^-1 mod (p-1)(q-1)
  4. m = c^d mod V
  5. POST /open            {"message": str(m)}  ->  the completion token

Step 2 is the pairwise form of "batch GCD" and is all the vault needs. The
solver also runs the real thing (product tree + remainder tree, the form that
scales to millions of numbers) over the whole register, as an independent
check that the register holds exactly one shared prime and that the vault is
one of its two owners. If that check disagrees, the run fails.

Standard library only. No randomness: a run is a pure function of the box.
Override the target with MINTMARK_URL (e.g. http://localhost:9100 from the host).
"""
import http.client
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request

BASE = os.environ.get("MINTMARK_URL", "http://app").rstrip("/")
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


def fetch_register():
    """GET /, retrying while the service is still striking its register."""
    deadline = time.time() + BOOT_WAIT
    while True:
        try:
            return call("/")
        except (OSError, http.client.HTTPException, ValueError, RuntimeError) as err:
            if time.time() > deadline:
                raise RuntimeError(f"no register from {BASE} after {BOOT_WAIT}s: {err}")
            time.sleep(0.5)


# --------------------------------------------------------------------------
#  Number theory
# --------------------------------------------------------------------------
def scan(vault, directory, v):
    """gcd of the vault with every other entry. Returns [(index, factor)]."""
    hits = []
    for i, x in enumerate(directory):
        if i == v:
            continue
        g = math.gcd(vault, x)
        if 1 < g < vault:
            hits.append((i, g))
    return hits


def batch_gcd(nums):
    """gcd(n_i, product of all the others) for every i, via product/remainder trees.

    With P the product of everything, (P mod n_i^2) / n_i is P / n_i mod n_i,
    so its gcd with n_i is the part of n_i shared with the rest of the list.
    """
    tree = [list(nums)]
    while len(tree[-1]) > 1:
        row = tree[-1]
        tree.append([math.prod(row[i:i + 2]) for i in range(0, len(row), 2)])
    rems = tree.pop()                                    # [P]
    while tree:
        row = tree.pop()
        rems = [rems[i // 2] % (x * x) for i, x in enumerate(row)]
    return [math.gcd(r // x, x) for r, x in zip(rems, nums)]


def inscription(m, size):
    """The text inside m if it is laid out as 00 02 | padding | 00 | text."""
    raw = m.to_bytes(size, "big")
    if raw[:2] != b"\x00\x02":
        return None
    _, sep, text = raw[2:].partition(b"\x00")
    if not sep or not text or not text.isascii():
        return None
    text = text.decode("ascii")
    return text if text.isprintable() else None


# --------------------------------------------------------------------------
#  The solve
# --------------------------------------------------------------------------
def main():
    box = fetch_register()
    directory = [int(x) for x in box["directory"]]
    v, e, c = int(box["v"]), int(box["e"]), int(box["c"])
    if len(directory) != int(box["N"]) or not 0 <= v < len(directory):
        raise RuntimeError("register is inconsistent (N, v, directory length)")
    vault = directory[v]
    say(f"[solve] register at {BASE}: N={len(directory)} entries of "
        f"{max(x.bit_length() for x in directory)} bits, vault v={v}, e={e}")

    # 2. The vault against every other entry.
    t0 = time.perf_counter()
    hits = scan(vault, directory, v)
    if len(hits) != 1:
        raise RuntimeError(f"expected one entry sharing a factor with the vault, "
                           f"found {len(hits)}")
    partner, p = hits[0]
    say(f"[solve] gcd scan, {len(directory) - 1} entries in "
        f"{(time.perf_counter() - t0) * 1000:.1f} ms: entry {partner} shares a "
        f"{p.bit_length()}-bit factor with the vault")

    # Independent check with a true batch GCD over the whole register.
    t0 = time.perf_counter()
    marked = {i: g for i, g in enumerate(batch_gcd(directory)) if g != 1}
    if marked != {v: p, partner: p}:
        raise RuntimeError(f"batch GCD disagrees: entries {sorted(marked)} carry a "
                           f"shared factor, expected exactly {sorted((v, partner))}")
    say(f"[solve] batch GCD over all {len(directory)} entries in "
        f"{(time.perf_counter() - t0) * 1000:.1f} ms: the only shared factor in the "
        f"register is between entries {v} and {partner}")

    # 3. Split the vault and invert e.
    q = vault // p
    if p * q != vault or q in (1, vault):
        raise RuntimeError("the shared factor does not split the vault")
    d = pow(e, -1, (p - 1) * (q - 1))
    say(f"[solve] vault = p * q with {p.bit_length()} + {q.bit_length()} bits; "
        f"private exponent recovered")

    # 4. Unseal.
    m = pow(c, d, vault)
    if pow(m, e, vault) != c or not 0 < m < vault:
        raise RuntimeError("recovered m does not reseal to c")
    text = inscription(m, (vault.bit_length() + 7) // 8)
    say(f"[solve] m recovered ({m.bit_length()} bits)"
        + (f'; inscription: "{text}"' if text else ""))

    # 5. Open.
    verdict = call("/open", {"message": str(m)})
    if verdict.get("opened") is not True or "token" not in verdict:
        raise RuntimeError(f"/open refused the recovered m: {verdict}")
    say("[solve] /open accepted the message")
    say(f"TOKEN: {verdict['token']}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, KeyError, TypeError, ValueError) as err:
        say(f"[solve] FAILED: {type(err).__name__}: {err}")
        sys.exit(1)
