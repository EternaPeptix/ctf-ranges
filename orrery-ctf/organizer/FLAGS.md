# Flags (organizer)

One flag, **earned** (not hardcoded): a `FLAG{...}` set at startup is returned by
`POST /submit` only to a term list equal (in `F_p[x0..x5]`) to the hidden polynomial.
Verified live via `scripts/solve.py` — `make check` reconstructs the polynomial from
32 evaluations and gets the token (exit 0), repeatably.

| Widget | Port | Technique required | Flag |
|--------|------|--------------------|------|
| orrery | 9500 | **Ben-Or–Tiwari / Prony** sparse interpolation (Berlekamp–Massey + root finding over F_p) | `FLAG{<random per boot>}` |

## The technique (why it's the whole point)
A hidden sparse polynomial `f` in 6 variables over a 301-bit prime field: ≤16 terms,
each exponent ≤20; the term count, exponents, and coefficients are all secret. You get
only **32 evaluations**. Dense interpolation is ~21⁶ ≈ 86M unknowns; variable-by-variable
needs hundreds of evals; working mod p blocks the "plug in a huge base, read digits" trick.

The decode: evaluate at the geometric points `x_i = (2ⁱ,3ⁱ,5ⁱ,7ⁱ,11ⁱ,13ⁱ)` for `i=0..31`.
Then `v_i = Σ_j c_j·m_jⁱ` (with `m_j` the j-th monomial at `(2,3,5,7,11,13)`) is a
**linear recurrence of order t**. Berlekamp–Massey gives the locator polynomial; its roots
`m_j` factor over `{2,3,5,7,11,13}` to reveal the exponent vectors; a Vandermonde solve gives
the coefficients. The prime exceeds the largest monomial value `30030²⁰`, so each `m_j` is
read back uniquely.

## Reference solver stats
- Spends exactly 32 evaluations, runs Berlekamp–Massey + root-finding (Cantor–Zassenhaus)
  mod p, factors the roots, and solves for the coefficients. Deterministic. Offline:
  2400/2400 random recoveries (term counts 1..16, including tight 16-term instances).
- `f` and the token are OS-random per boot; the 32-budget is strict per gear train, and a
  correct submission **winds a fresh gear train with a full budget** (token fixed at boot),
  so `make check` is a plain `verify.sh` and stays green however often it runs.

## Notes
- No scoreboard: single-service range; the flag is the `/submit` token.
- `orrery_net` is pinned to an explicit `10.92.0.0/24` (host default pools exhausted); the
  compose has a healthcheck so `up --wait` blocks until the service answers.
- The budget is enforced under a lock (concurrency-tested: 32 answered, the rest 429);
  malformed requests are free; `/submit` compares polynomials (like terms combined); secrets
  are never logged. `p = 2³⁰⁰+157` with a startup primality + size assertion.
- Built by Fable 5.2 ("a brass orrery with six arms and a hidden gear train," its creative
  choice) to spec; serve.py and the solver were reviewed here, the token aligned to
  `FLAG{...}`, and the one-shot budget switched to restock-on-solve so `make check` matches
  the sibling boxes (a plain `verify.sh`).
