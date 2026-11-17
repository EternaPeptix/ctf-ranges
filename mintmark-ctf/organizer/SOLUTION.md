# mintmark -- solution (spoilers)

The vault's number cannot be factored. It does not have to be. **One other
entry of the directory was built with one of the vault's two primes**, and the
greatest common divisor of two 1024-bit numbers takes about five microseconds.
`scripts/solve.py` is that observation and four lines of textbook RSA:
standard library only, no randomness, one `GET /` and one `POST /open`.

In the mint's terms: two seals were struck with the same die. Numismatists
call two coins that share a die a *die link*, and find them by laying the
whole hoard side by side. That is the method here too.

## 1. How the register is built

`app/serve.py`, `strike()`:

- `2N - 1 = 255` pairwise distinct 512-bit primes are drawn (pure-stdlib
  Miller-Rabin, see section 5).
- One of them, `p`, is the **shared prime**. Two distinct indices `v`
  (the vault, public) and `b` (the partner, secret) are chosen at random, and
  `V_v = p * q_v`, `V_b = p * q_b`.
- Every other entry gets two primes of its own. Every prime other than `p`
  appears in exactly one entry.
- `m` is laid out like a PKCS#1 v1.5 block, `00 02 | 73 nonzero random bytes |
  00 | text`, read as a big-endian integer. The leading bytes make
  `m < 2^1010 < V`; the padding carries about 583 random bits. The text is
  `Old Mint strongroom, coffer NNN: two seals, one die.`
- `c = m^65537 mod V_v`.

So in the whole register `gcd(V_i, V_j) = 1` for every pair except
`gcd(V_v, V_b) = p`.

## 2. Why the vault cannot be opened on its own

- `V` is 1024 bits, the product of two random 512-bit primes with their top
  two bits set. The public factoring record for numbers of this shape is 829
  bits (RSA-250).
- No small factors: both primes are 512 bits. Trial division, Pollard rho and
  ECM find nothing.
- Not Fermat-close: the generator redraws unless `|p - q|` has at least 412
  bits (in practice it has about 500 to 510).
- `e = 65537` with a full-size random `m`: no small-exponent root, no
  short-pad or stereotyped-message attack (the unknown part of `m` is far
  larger than `V^(1/e)`), and there is only one ciphertext, so nothing to
  broadcast or relate.
- `/open` is a yes/no oracle on an integer with about 583 unknown bits. It
  compares in constant time and leaks nothing else.
- `GET /` is a constant: it is serialised once at start, so there is no state
  to probe.

The only thing that distinguishes `V` from an honest RSA modulus is its
relationship to one other number in the list.

## 3. The method

```
box       = GET /
D, v, e, c = box.directory, box.v, box.e, box.c
V         = D[v]

for i != v:                       # 127 gcds, under a millisecond in total
    g = gcd(V, D[i])
    if 1 < g < V:  p = g          # exactly one i does this

q = V // p
d = e^-1 mod (p-1)(q-1)           # pow(e, -1, (p-1)*(q-1)); lcm(p-1, q-1) works too
m = c^d mod V                     # pow(c, d, V)

POST /open {"message": str(m)}    # -> {"opened": true, "token": "FLAG{...}"}
```

Why `g` is exactly `p`: `V = p * q_v` and `V_b = p * q_b` with `q_v != q_b`
both prime, so the only common divisor above 1 is `p`. For every other `i` the
two numbers have no prime in common and the gcd is 1.

Why it is cheap: Euclid's algorithm on two `k`-bit numbers is `O(k^2)` bit
operations, against the sub-exponential cost of factoring one of them. The
whole scan is 127 gcds.

A typical run of the reference solver:

```
[solve] register at http://app: N=128 entries of 1024 bits, vault v=36, e=65537
[solve] gcd scan, 127 entries in 0.8 ms: entry 59 shares a 512-bit factor with the vault
[solve] batch GCD over all 128 entries in 101.6 ms: the only shared factor in the register is between entries 36 and 59
[solve] vault = p * q with 512 + 512 bits; private exponent recovered
[solve] m recovered (1010 bits); inscription: "Old Mint strongroom, coffer 036: two seals, one die."
[solve] /open accepted the message
TOKEN: FLAG{mintmark_two_seals_one_die_c7b40fc3442dd95efa8073b5}
```

## 4. Batch GCD

Scanning the vault against everything is the pairwise form of **batch GCD**,
and it is enough here because the vault is known. When the weak key is *not*
known in advance (the situation of the 2012 internet-wide surveys of TLS and
SSH keys, which found shared primes in a fraction of a percent of all keys),
all pairs would be `N(N-1)/2` gcds. The product-tree / remainder-tree
algorithm computes, for every `i` at once,

```
g_i = gcd(V_i, (P mod V_i^2) / V_i)     with  P = V_0 * V_1 * ... * V_{N-1}
```

`(P mod V_i^2) / V_i` is `P / V_i` reduced modulo `V_i`, so `g_i` is the part
of `V_i` that it shares with the rest of the list. `P` is built bottom-up as a
product tree and pushed back down as a remainder tree, squaring the modulus at
each node.

`solve.py` implements it in about ten lines (`batch_gcd`) and uses it as an
independent audit: it must mark exactly two entries, the vault and the partner
found by the scan, both with the same `g`. At `N = 128` it is slower than the
scan (about 0.1 s against under 1 ms), because the scan only needs the vault's
row of the pair table. It pays off when every pair matters and the list is
long.

## 5. Correctness guarantees in the generator

Checked by `audit()` before the service listens. A failed assertion stops the
process, and `restart: unless-stopped` starts a fresh one.

- **Exactly one shared prime.** The `2N` prime slots hold `2N - 1` distinct
  values, and the repeated one sits in the vault and in the partner.
- `gcd(V, V_i) == 1` for every non-partner `i`, and `gcd(V, V_partner) == p`.
- The same over the whole register: all `N(N-1)/2` pairs are coprime except
  `{v, partner}`.
- Every prime has exactly 512 bits and every entry exactly 1024 bits, so sizes
  give nothing away.
- **`e` is invertible.** `random_prime()` rejects any prime `p` with
  `p mod 65537 == 1`, so `gcd(e, (p-1)(q-1)) == 1` for every entry, the vault
  included; the audit asserts it again for the vault.
- `0 < m < V`, `c == m^e mod V`.
- **Self-solve.** The audit then repeats the solver's steps from the public
  values only (scan, split, invert, decrypt) and asserts it gets `m` back.

Miller-Rabin (`is_probable_prime`): one gcd against the product of the primes
below 2000, then base 2, then 23 random bases. A composite survives the random
bases with probability at most `4^-23`; for random 512-bit candidates the true
rate is far lower. Below `1999^2` (about four million) the function is exact:
the gcd is a complete trial division there.

## 6. What does not work

- Factoring `V` directly, by any method, in any reasonable time.
- Looking for small factors, a small `d`, close primes, a small `m`, or a
  second ciphertext. None is there.
- Guessing at `/open`, or timing it.
- Looking for a pattern in the order of the directory: `v` and the partner are
  two indices drawn uniformly at random.

## 7. Reproducing

```
make up && make check          # PASS, prints TOKEN: FLAG{...}
make reset && make check       # new primes, new pair, new m, new token; PASS again
MINTMARK_URL=http://localhost:9100 python3 scripts/solve.py    # from the host
```
