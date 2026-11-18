# fathom -- solution (spoilers)

**Technique: minimal polynomial from an approximation, by integer LLL lattice
reduction.** The reference implementation is `scripts/solve.py` (standard
library only, exact integer arithmetic throughout, about 5 ms of LLL).

## 1. Why the obvious things fail

- `/submit` is a yes/no oracle over `(2*10^5 + 1)^7 ~ 1.28 * 10^37`
  coefficient vectors. No search gets anywhere.
- The unknowns are integers and the data is one real number. The condition
  `c0 + c1*alpha + ... + c6*alpha^6 = 0` is a single linear equation in seven
  unknowns: over the reals it has a six-dimensional solution space, so
  least squares / root fitting returns *a* real solution, never the integer
  one. What pins P down is "small integers", and that is a lattice condition.

## 2. The lattice

Read `A = floor(alpha * 10^k)` and put `a = A / 10^k`, so `|a - alpha| < 10^-k`.
Pick a weight `10^s` with `s < k` and set

```
R_i = round(10^s * a^i)        i = 0..6        (exact: round(A^i / 10^(k*i - s)))
```

The lattice is spanned by the seven rows of the 7 x 8 integer matrix

```
b_i = ( R_i , e_i )            e_i = i-th unit vector of Z^7
```

A lattice vector is `( sum c_i R_i , c0, ..., c6 )` for integers `c_i`: the
last seven coordinates are a polynomial, the first is `10^s` times its value
at alpha, up to rounding. So:

- for `c = P` the vector is `(noise, P)`, with `|noise| <= sum|c_i| / 2`,
  length at most about `4.4 * 10^5`;
- for any other polynomial `D` of comparable size the first coordinate is
  about `10^s * |D(alpha)|`, and `D(alpha)` cannot be very small (section 4),
  so the vector is enormous.

`(noise, P)` is therefore the shortest vector by a wide margin, and LLL, whose
first output vector is within a factor `2^((n-1)/2) = 8` of the shortest, has
to return it. Read the coefficients off its last seven coordinates, fix the
sign so `c6 > 0`, submit.

**About the weight.** The lattice is often written as
`( C * round(10^t * alpha^i), e_i )` with a separate multiplier `C`. Only the
total weight on the first coordinate, measured against the precision actually
known, matters: a multiplier applied *after* rounding scales the rounding
noise of the true relation by `C` as well and buys nothing. So the solver
puts the whole weight inside the rounding (`C = 1`, `t = s = 80`) and keeps
`s` well below the number of digits read (`k = 120`), which makes the noise
from the unread tail of alpha negligible. The weight `10^s` is what forces
`sum c_i alpha^i ~ 0`.

## 3. Exact integer LLL

Entries have 80 to 110 digits, so floating-point Gram-Schmidt is out.
`lll_reduce` is the all-integer LLL (de Weger; Cohen, *A Course in
Computational Algebraic Number Theory*, Alg. 2.6.7) with `delta = 3/4`. In
place of the rational Gram-Schmidt coefficients it carries

```
D[i]      = Gram determinant of the first i rows        (D[0] = 1)
lam[i][j] = D[j+1] * mu[i][j]                           (j < i)
```

which are integers; every division in the update formulas is exact, the
Lovasz test is `4*D[k+1]*D[k-1] >= 3*D[k]^2 - 4*lam[k][k-1]^2`. There is no
precision parameter and nothing to tune. On the 7 x 8 basis it takes a few
milliseconds.

## 4. How many digits suffice

Write `H = 10^5`, `n = 7`.

**Lower limit (counting).** `10^37.1` candidates, so fewer than 38 digits
cannot determine P even in principle.

**In practice.** The lattice has determinant about `10^s`, so a "random"
vector in it has length about `10^(s/7)`, while the target has length about
`3 * 10^5`. The target stands out once `10^(s/7)` clears that by the LLL
factor, i.e. from `s` around 40. Measured on 300 random secrets per row
(first LLL vector equal to `+-P`):

| weight `s` | 30 | 34 | 36 | 38 | 40 | 42 .. 80 |
|---|---|---|---|---|---|---|
| success | 2/300 | 23/300 | 106/300 | 287/300 | 300/300 | 300/300 |

Rule of thumb: `(degree + 1) * log10(H)` digits plus a handful.

**Provably.** Let `v = (noise, P)`. Then `|v| <= H * sqrt(7 + 3.5^2) < 4.39 * 10^5`
and LLL's first vector has length at most `T = 8 * |v| < 3.51 * 10^6`. Suppose
a lattice vector `w = (sum d_i R_i, d)` with `|w| <= T` is not a multiple of
`v`. Then `D(x) = sum d_i x^i` is nonzero, has degree at most 6 and is not a
multiple of P; P is irreducible, so the resultant `Res(P, D)` is a nonzero
integer:

```
1 <= |Res(P, D)| = c6^deg(D) * prod_j |D(alpha_j)|          (alpha_j = roots of P)
```

Bounding the five factors with `alpha_j != alpha` by
`|D(alpha_j)| <= |d|_1 * max(1, |alpha_j|)^deg(D)` and collecting the root
sizes into the Mahler measure `M(P) <= |P|_2 <= sqrt(7) * H` (Landau):

```
|D(alpha)| >= 1 / ( |d|_1^5 * M(P)^6 )
           >= 1 / ( (sqrt(7)*T)^5 * (sqrt(7)*H)^6 )  >  4.2 * 10^-68
```

The first coordinate of `w` is at least
`10^s * |D(alpha)| - |d|_1 / 2 - 1` (rounding, and the tail of alpha, see
below), which exceeds `T` as soon as `10^s > 1.94 * 10^74`. So

> **`s >= 75` guarantees that LLL's first vector is `+-(noise, P)`**,
> for every P the service can draw.

**Guard digits (`k - s`).** `R_i` is built from `a`, not alpha. The error it
introduces in a first coordinate is at most
`10^(s-k) * 6 * |d|_1 * (|alpha| + 1)^5`. Cauchy's bound gives
`|alpha| < H + 1`, so `k - s >= 34` keeps this below 1/2 for every possible
alpha; for an ordinary alpha (`|alpha| < 9`) 14 guard digits do. This matters:
with a tiny leading coefficient alpha can be as large as `10^5`, and
measured on 100 such secrets at `s = 80`, recovery is 0/100 with 0 or 5 guard
digits and 100/100 from 10 up. For ordinary alpha, 0 guard digits already
gave 300/300, but there is no reason to run that close.

**What the solver does.** `provable_digits(6, 10^5)` evaluates the two bounds
above, `(75, 34)`; the solver adds a margin and uses **`s = 80`, `k = 120`**
(one `/digits` request), then a second reading at `K = 160` for the check.
So: about 45 to 50 digits are enough in practice, **109 digits are provably
enough**, the reference asks for 120.

## 5. Checking the candidate

Before submitting, `recover()` verifies, for each reduced row in order of
length:

1. degree exactly 6 and height at most `10^5`;
2. canonical form: divide by the gcd, make `c6 > 0`;
3. **extra digits**: with `B = floor(alpha * 10^160)` from a second request
   (40 digits the lattice never saw), `Q(B / 10^160) < 0 < Q((B+1) / 10^160)`
   in exact integer arithmetic. So Q has a root within `10^-160` of alpha, and
   it goes from minus to plus there, as it must at the largest root of a
   polynomial with positive leading coefficient. By the resultant bound of
   section 4 a polynomial of this height that is not `+-P` cannot have a root
   that close to alpha, so this check alone is conclusive;
4. **irreducibility**, as an independent sanity check: factor Q modulo small
   primes (distinct-degree factorisation); the degree of a rational factor
   must be a subset sum of the factor degrees modulo every prime, and if only
   0 and 6 survive, Q is irreducible. The service accepts a secret only if
   this same test, with the same primes, succeeds, so it always succeeds on P.

If nothing passes, `main()` retries with `(s, k) = (110, 160)` and
`(150, 210)`. In 2700 offline recoveries (1200 random secrets and 1500 edge
cases: alpha near `10^5`, alpha near 0, negative alpha, heights of 3 and of
exactly `10^5`) the first attempt always succeeded and the first LLL vector
was always `+-P`.

## 6. Step by step by hand

```
GET  /                         degree 6, height 100000, max_n 1000
POST /digits {"n": 120}        A
R_i = round(A^i / 10^(120*i - 80))            i = 1..6,   R_0 = 10^80
rows (R_i, e_i)   ->   LLL   ->   first row (noise, c0..c6)
POST /digits {"n": 160}        B;   check sign change of the candidate
POST /submit {"coeffs": [c0..c6]}   (c6 > 0)      -> FLAG{...}
```

Any integer-relation method works equally well (PSLQ on
`1, alpha, ..., alpha^6` at comparable precision, or an
`algdep`/`lindep`/`minpoly`-style library call). The box only requires the
answer.

Pitfalls a solver tends to hit:

- doing any of it in floats (the readings do not fit in a double; the
  relation is invisible below ~40 digits);
- using too few digits: below ~38 the shortest vector is not P;
- weighting with all `k` digits while alpha is large (no guard digits);
- submitting `-P`: LLL returns the vector up to sign, the service wants
  `c6 > 0`;
- for a negative alpha, `digits` is a floor (toward minus infinity), not a
  truncation toward zero. `a = A / 10^k` is still within `10^-k` of alpha.

## 7. How the service produces exact digits

`app/serve.py`, at startup:

1. draw `c0..c6` uniformly in `[-10^5, 10^5]`, `c6 != 0`; flip the sign so
   `c6 > 0`; require gcd 1;
2. require the irreducibility certificate of section 5 (primes below 400);
   redraw otherwise;
3. build a Sturm chain for P (integer coefficients), count real roots inside
   Cauchy's bound, redraw if there are none, and bisect with the chain until
   a rational `lo` is found with *no* real root other than alpha in
   `[lo, +inf)`. Then `P(x) < 0` exactly for `lo <= x < alpha` and `P(x) > 0`
   for `x > alpha`.

`floor(alpha * 10^k)` is then the largest integer `m` with
`10^(6k) * P(m / 10^k) = sum c_i * m^i * 10^(k*(6-i)) < 0`, found by integer
bisection on that sign. No floats and no rounding anywhere, so every digit is
exact; alpha is irrational, so the sign is never zero. The best reading so
far is cached, a longer request refines it and a shorter one is a division.
A cold `n = 1000` request takes a fraction of a second.

P and the token are not logged. To see P for the running instance, run the
solver (`make check` prints it).
