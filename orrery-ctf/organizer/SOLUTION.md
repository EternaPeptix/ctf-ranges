# orrery -- solution (organizer, spoilers)

## The puzzle

The service hides

```
f(x0..x5) = sum_{j=1..T} c_j * x0^e_j0 * ... * x5^e_j5   (mod p),     p = 2^300 + 157
```

with `T <= t = 16` terms, every exponent in `0..20`, every `c_j` nonzero mod
`p`. `T`, the exponents and the coefficients are secret. `POST /eval` answers
`f(x) mod p` at most **32 times**; `POST /submit` releases the token only for
`f` itself.

## Why the obvious things fail

- **Dense interpolation.** There are `21^6 = 85,766,121` candidate monomials,
  so a dense solve has that many unknowns and 32 equations.
- **One variable at a time.** Fixing five variables and interpolating the sixth
  needs 21 points per univariate slice, and there are many slices: hundreds to
  thousands of evaluations in total (Zippel-style sparse interpolation is
  about `n * d * t ~ 2000`).
- **Huge base, read the digits.** Over the integers `f(B, B^21, B^441, ...)`
  for a large `B` would print the terms as digits. Here every answer is a
  301-bit residue, the Kronecker exponent runs up to `21^6 - 1` so the powers
  of `B` wrap around `p` at once, and the coefficients are themselves random
  300-bit residues.
- **Guessing through `/submit`.** It is an equality oracle for the whole
  polynomial: one bit, and only for an exact guess.

## The method: Ben-Or--Tiwari (Prony's method over F_p)

The intended technique is the sparse interpolation algorithm of Ben-Or and
Tiwari (1988), which is Prony's 1795 method for sums of exponentials carried
over to a finite field. It needs `2t` evaluations: exactly the budget.

### 1. Evaluate along a geometric progression of primes

Ask for the 32 points

```
x_i = (2^i, 3^i, 5^i, 7^i, 11^i, 13^i),      i = 0 .. 31.
```

A monomial `x0^a x1^b x2^c x3^d x4^e x5^g` takes the value `(2^a 3^b 5^c 7^d
11^e 13^g)^i` at `x_i`. Writing `m_j = 2^e_j0 * 3^e_j1 * 5^e_j2 * 7^e_j3 *
11^e_j4 * 13^e_j5` for the j-th monomial evaluated at `(2, 3, 5, 7, 11, 13)`,

```
v_i = f(x_i) = sum_j c_j * m_j^i      (mod p).
```

So the answers are a sum of `T` geometric sequences with unknown ratios `m_j`
and unknown weights `c_j`.

Two facts make the `m_j` usable, and both are why `p` is as large as it is:

- By unique factorisation, different exponent vectors give different integers
  `m_j`, and the exponent vector can be read back from `m_j` by trial division.
- `m_j <= (2*3*5*7*11*13)^20 = 30030^20 ~ 2^297.5 < p`. So the `m_j` stay
  distinct mod `p`, and the least non-negative residue of `m_j` *is* the
  integer `m_j`. Nothing wraps. (`p / 30030^20` is about 5.7.)

### 2. Berlekamp--Massey: the locator polynomial

Let `L(z) = prod_j (z - m_j) = z^T + l_1 z^(T-1) + ... + l_T`. For every
`n >= T`,

```
v_n + l_1 v_(n-1) + ... + l_T v_(n-T) = sum_j c_j m_j^(n-T) L(m_j) = 0,
```

so `(v_i)` satisfies a linear recurrence of order `T` whose characteristic
polynomial is `L`. It satisfies none shorter: the `T x T` Hankel matrix
`[v_(i+k)]` equals `V^T diag(c) V` with `V` the Vandermonde matrix of the
`m_j`, which is invertible because the `m_j` are distinct and the `c_j`
nonzero mod `p`.

Berlekamp--Massey over `F_p` returns the shortest recurrence of a sequence
from its first `2T` values. We have `32 >= 2T`, so it returns `L` and, as a
by-product, the secret term count `T = deg L`. This costs on the order of a
thousand modular multiplications.

### 3. Roots of the locator: Cantor--Zassenhaus

`L` is a product of distinct linear factors over `F_p`, and its roots are the
`m_j`. For a random `a`, the polynomial `(z + a)^((p-1)/2) - 1` vanishes at
exactly those `r` for which `r + a` is a nonzero square, so

```
gcd( L(z), (z + a)^((p-1)/2) - 1  mod L(z) )
```

splits off about half of the roots. Recurse on both parts until everything is
linear. The power is computed by square-and-multiply modulo `L` (degree at most
16, about 300 squarings). The solver seeds its random source with a constant,
so a run is a deterministic function of the service's answers. As a guard it
first checks `gcd(L, z^p - z) = L`, i.e. that `L` really splits into distinct
linear factors, so an inconsistent input fails cleanly instead of looping.

### 4. Exponents: factor each root

Each root is an integer below `p` whose only prime factors are 2, 3, 5, 7, 11
and 13. Divide them out; the six multiplicities are the exponent vector
`(e_j0, ..., e_j5)`. If anything other than 1 is left, or a multiplicity
exceeds 20, something is wrong (it never is).

### 5. Coefficients: a Vandermonde system

With the `m_j` known, the first `T` evaluations are linear in the weights:

```
sum_j c_j * m_j^i = v_i,      i = 0 .. T-1.
```

The matrix is a (transposed) Vandermonde matrix in distinct `m_j`, hence
invertible; plain Gauss--Jordan elimination mod `p` on a `16 x 16` system is
instant.

### 6. Cross-check and submit

The solver recomputes all 32 values from the recovered terms (when `T < 16` the
surplus evaluations are a genuine check), then posts the terms to `/submit`
and prints `TOKEN: FLAG{...}`.

### Why 32, and why it is tight

A `T`-sparse polynomial has `2T` unknowns in this picture: `T` ratios and `T`
weights. `2T` evaluations determine them, and `t = 16` gives `2t = 32`. An
instance with 16 terms cannot be recovered by this method with 31 answers, so
the budget has no slack at all: a solver that spends even one evaluation on
looking around can be left unable to finish. That is the trap the brief warns
about ("decide what you are going to ask before you ask it").

## Reference solver

`scripts/solve.py`, standard library only, about 160 lines of code:

```
call()                 GET with retry while the service boots; POST without retry (evals cost)
pdivmod/pmulmod/...    F_p[z] arithmetic on coefficient lists
berlekamp_massey()     step 2
roots()                step 3 (random.Random(1729))
exponents()            step 4
solve_linear()         step 5
recover()              steps 2-6 on a list of values; raises ValueError on any inconsistency
main()                 reads GET /, spends the 32 evaluations, submits, prints TOKEN:
```

It reads `p`, the bounds and the remaining budget from `GET /`, refuses to
start if fewer than 32 evaluations are left or if `p <= 30030^max_degree`, and
never retries a `POST`.

Offline check of `recover()` against a local model of the service: 2400 random
polynomials (150 for each term count 1..16), 200 polynomials with all
exponents in 0..1, and a hand-built 16-term corner case (all-20 exponents, the
constant term, coefficients 1 and p-1, tiny monomial values) were all
reconstructed exactly; the slowest single reconstruction took 0.34 s. A
17-term polynomial is rejected with `ValueError`, as it should be.

Run it by hand from the host with
`ORRERY_URL=http://localhost:9500 python3 scripts/solve.py`.

## Other routes that are fine

- **Kronecker substitution plus discrete logs.** Pick `g` of large order and
  evaluate at `x_i = (g^i, g^(21 i), g^(441 i), ..., g^(21^5 i))`. The ratios
  become `g^E_j` with `E_j = sum_k e_jk 21^k < 21^6`, and each `E_j` falls to
  baby-step/giant-step in about 9300 steps. Same idea, same 32 evaluations.
- **A Hankel solve instead of Berlekamp--Massey** (try `T = 16, 15, ...` until
  the Hankel matrix is invertible), or any other textbook root finder over
  `F_p` in place of Cantor--Zassenhaus.
- **Fewer evaluations when `T < 16`.** `2T` answers suffice, so a solver may
  stop early and let `/submit` confirm. The reference solver does not bother.

## Service notes

- **Generation.** `T` is uniform in 8..16, the exponent vectors are distinct
  and uniform in `{0..20}^6`, the coefficients uniform in `1..p-1`, all from
  `secrets.SystemRandom`. The floor of 8 is not told to players (the brief says
  "at most 16"); it only keeps degenerate instances out, since a one-term
  polynomial, for example, falls to seven evaluations and no theory at all.
- **Budget.** A counter under a lock; every answered `/eval` increments it,
  repeats included; at 32 the endpoint returns HTTP 429. Malformed requests are
  rejected before the counter is touched. The counter resets when the process
  restarts (which redraws `f` and the token) and when a correct submission winds
  a fresh gear train (which redraws `f` and resets the counter; the token is
  fixed at startup). Verified: 64 concurrent requests yield exactly 32 answers
  and 32 refusals.
- **Submission check.** The submitted list is reduced to a canonical
  `{exponent vector: coefficient mod p}` map (like terms added, zeros dropped)
  and compared with the secret map, so the test is equality in
  `F_p[x0..x5]`, not equality of functions: `x^(e+p-1)` in place of `x^e` is
  rejected.
- **`make check` is a plain `scripts/verify.sh`.** The reference solver consumes
  the whole budget, so a correct submission winds a fresh gear train (a new `f`
  with a full budget; the token is fixed at startup). That is what lets a second
  `make check` succeed against the same running service, matching the sibling
  boxes. Every `make check` is a proof on a fresh random instance.
- **Token.** `FLAG{<32 hex digits>}`, fresh per startup, held only in memory.
  `scripts/verify.sh` accepts any `TOKEN: WORD{...}` line.
