# quorum -- solution (organizer, spoilers)

**Technique: Chinese remaindering with errors, decoded by rational
reconstruction.** It is the integer counterpart of Berlekamp-Welch decoding of
Reed-Solomon codes: the residues `N mod p_i` are a codeword, the liars are the
errors, and the product of the liar primes plays the role of the error-locator
polynomial. Reference implementation: `scripts/solve.py` (standard library only).

## Setup

| Symbol | Meaning | Value in this box |
|---|---|---|
| `N` | the secret | random, exactly 2000 bits |
| `B` | public bound, `0 < N < B` | `2^2000` |
| `p_0..p_{M-1}` | public distinct primes | `M = 250`, each in `[2^19, 2^20)` |
| `r_i` | what `POST /residue {"i": i}` states | `N mod p_i` if honest, a fixed wrong value if a liar |
| `L` | the set of liar indices (secret) | `|L| <= 70` (the service marks exactly 70) |
| `Mprod` | `p_0 * p_1 * ... * p_{M-1}` | about `2^4890` |
| `E` | `prod_{i in L} p_i`, the "error locator" | below `2^1400` |
| `Emax` | product of the 70 largest primes, so `E <= Emax` | below `2^1400` |

## The method

1. **Collect.** `GET /` for the primes, `B` and `max_liars`; `POST /residue`
   for every `i` to get `r_0..r_249`. 250 requests, about 0.2 s.

2. **CRT everything, lies included.** Compute the unique `R` with
   `R = r_i (mod p_i)` for all `i` and `0 <= R < Mprod`. `R` is not `N`: it is
   a number of about 4890 bits.

3. **The key identity.**

   ```
   E * R  =  E * N   (mod Mprod)
   ```

   Check it prime by prime. For an honest `p_i`: `R = r_i = N (mod p_i)`. For a
   liar `p_i`: `p_i` divides `E`, so both sides are 0. All the `p_i` are
   distinct primes, so the congruence holds modulo their product.

   So there is a pair `(a, b) = (E*N, E)` with

   ```
   a = b * R (mod Mprod),     0 < b <= Emax,     0 < a < B * Emax
   ```

   and both are tiny next to `Mprod`: `b` has at most 1400 bits and `a` at
   most 3400, against 4890.

4. **Rational reconstruction.** Run the extended Euclidean algorithm on
   `(Mprod, R)`, keeping for every remainder `a_j` its cofactor `b_j` with
   `a_j = b_j * R (mod Mprod)`:

   ```
   a0, b0, a1, b1 = Mprod, 0, R, 1
   while a1 >= B * Emax:
       q = a0 // a1
       a0, b0, a1, b1 = a1, b1, a0 - q*a1, b0 - q*b1
   a, b = a1, abs(b1)
   ```

   The first row whose remainder is below `B * Emax` is exactly `(E*N, E)`.

5. **Divide and check.** `N = a / b` (the division is exact). Then
   `N mod p_i != r_i` for exactly the liar indices, there are at most 70 of
   them, and `b` equals the product of their primes. The solver asserts all
   three before it submits, so a wrong answer is never sent.

6. **Submit.** `POST /submit {"N": "<decimal>"}` returns
   `{"solved": true, "token": "FLAG{...}"}`.

The whole computation after the residues are in takes a few milliseconds.

## The parameter inequality

Recovery is guaranteed, for every choice of liars and every choice of lies,
whenever

```
2 * B * Emax^2  <  Mprod
```

with `Emax` the product of the `max_liars` largest primes (the worst case for
`E`).

**It always holds here.** `Mprod = Emax * (product of the 180 smallest
primes)`, so the inequality is the same as `2 * B * Emax < product of the 180
smallest primes`. With every prime in `[2^19, 2^20)`:

```
2 * B * Emax  <  2 * 2^2000 * (2^20)^70  =  2^3401  <  2^3420  =  (2^19)^180  <=  product of the 180 smallest
```

That is 19 bits to spare for *any* 250 distinct 20-bit primes. For a random
draw the margin is much larger: typically `2*B*Emax^2` has about 4786 bits and
`Mprod` about 4888, roughly 100 bits of slack (the smallest margin seen in
2000 simulated draws was 89 bits).

The back-of-envelope version, "250 primes x 20 bits gives `Mprod ~ 2^5000`,
`E < 2^1400`, so `2^4801 < 2^5000`", overstates `Mprod`: 20-bit primes average
about 19.55 bits, so `Mprod` is about `2^4890`, not `2^5000`. The inequality
holds all the same, by the argument above.

`app/serve.py` evaluates the inequality on the actual draw at startup
(`recovery_check`) and exits instead of serving if it fails. `scripts/solve.py`
evaluates it again from the public values before decoding.

## Why step 4 lands on the right row

Write `m = Mprod`. Rows of the extended Euclidean algorithm on `(m, R)` have
remainders `a_j` strictly decreasing to 0, cofactors `|b_j|` non-decreasing,
and `a_j = b_j * R (mod m)`. The fractions `s_j / b_j` (with `a_j = s_j*m +
b_j*R`) are, up to sign, exactly the continued-fraction convergents of `R / m`.

*The true pair is a row.* Put `k = (E*R - E*N) / m`, an integer by the key
identity. Then

```
| R/m - k/E |  =  E*N / (E*m)  =  N / m  <  1 / (2 * E^2)
```

because `2 * N * E^2 < 2 * B * Emax^2 < m`. By Legendre's theorem a fraction
that close is a convergent of `R/m`. It is already in lowest terms: if `g`
divided both `k` and `E`, then `(E/g) * R = (E/g) * N (mod m)`, and since
`R != N` modulo every liar prime, every liar prime would have to divide `E/g`,
forcing `g = 1`. So some row has `|b_j| = E`, and its remainder is
`|E*R - k*m| = E*N`.

*No earlier row stops the loop.* Suppose a row `j` before it had
`a_j < B * Emax`. Its cofactor satisfies `|b_j| <= E <= Emax`. Both `(a_j, b_j)`
and `(E*N, E)` satisfy `a = b*R (mod m)`, so `a_j * E - E*N * b_j` is a multiple
of `m`, and

```
| a_j * E - E*N * b_j |  <  B*Emax * Emax + B*Emax * Emax  =  2 * B * Emax^2  <  m
```

so it is zero: `a_j / b_j = N`. But `a_j / |b_j|` is strictly decreasing in
`j`, so two different rows cannot have the same ratio. Hence the first row
with remainder below `B * Emax` is `(E*N, E)`, and `N = a / b`.

The same bound gives **uniqueness** of the answer: two integers below `B` that
each disagree with at most 70 residues agree with each other modulo at least
110 of the primes, whose product exceeds `2^2090 > B`, so they are equal.

Fewer liars than 70 (including none) need no special handling: `E` is smaller,
the argument is unchanged, and the loop stops at the same kind of row.

## What does not work

- **Plain CRT** over all 250 residues: returns `R`, about 4890 bits, unrelated
  to `N` in any visible way.
- **Guessing a clean subset.** About 103 honest primes are needed before their
  product exceeds `B`. With 70 liars among 250, a random 103-subset is clean
  with probability `C(180,103) / C(250,103)`, about `2^-67`.
- **Asking again.** A liar's value is fixed at startup; repeated queries are
  byte-identical.
- **Probing `/submit`.** It reveals equality with `N` and nothing else.

A 2-dimensional lattice reduction (Lagrange/Gauss on the rows `(Mprod, 0)` and
`(R, 1)`, suitably scaled) finds the same short vector `(E*N, E)`; it is the
same computation as the Euclidean algorithm in other clothes.

## Run the reference

```
make up
make check
```

Expected output (bit counts vary by a few with the draw; the token is random
per start):

```
[solve] rules at http://app: 250 primes of 20..20 bits, N < 2^2000, at most 70 liars
[solve] 250 residues collected in 0.15 s
[solve] plain CRT: R has 4891 bits modulo a 4892-bit product -- not N, the lies are folded in
[solve] 2*B*Emax^2 has 4786 bits < Mprod with 4892 bits: recovery is guaranteed
[solve] a/b with b of 1372 bits gives N of 2000 bits; 180 residues agree, 70 witnesses lied, and b is exactly the product of their primes
[solve] /submit accepted N
TOKEN: FLAG{quorum_4ed43cf150255fec1331d5fd3bf7e62c}
[verify] PASS: N recovered despite the liars, token returned by /submit
```

`make check` exits 0 only if the `TOKEN: FLAG{...}` line is present.

## Organizer notes

- The token is `FLAG{quorum_<32 hex>}`, minted at startup, returned only by
  `POST /submit` for the exact `N`. `make reset` gives a new one, along with
  new primes, a new `N` and a new liar set.
- The service always marks exactly 70 liars (constant `LIARS` in
  `app/serve.py`), the hardest case the public promise allows. The solver does
  not rely on that.
- A liar's value is uniform over the `p_i - 1` wrong residues, so nothing about
  a single answer distinguishes a liar from an honest witness.
- The solver is deterministic: no randomness, no search, no retries beyond
  waiting for the service to come up.
