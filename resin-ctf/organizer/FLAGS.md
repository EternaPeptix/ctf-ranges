# Flags (organizer)

One flag, **earned** (not hardcoded): a fresh `FLAG{...}` is minted at startup and
returned by `POST /submit` only to a wiring whose Laplacian exactly matches the
hidden one. Verified live via `scripts/solve.py` — `make check` recovers the whole
graph from effective-resistance readings alone and gets the token (exit 0),
repeatably across resets.

| Widget | Port | Technique required | Flag |
|--------|------|--------------------|------|
| resin | 9600 | effective resistance is a **squared Euclidean distance** in Laplacian-pseudoinverse geometry; recover the Laplacian by a bordered-matrix inverse | `FLAG{<random per boot>}` |

## The technique (why it's the whole point)
30 studs; you may only ask the exact effective resistance `R_ij` between any two.
Every pair has a finite reading, so nothing local reveals adjacency and "small
reading ⇒ wire" is false (the service even guarantees some unwired pair reads lower
than some wired pair, so no threshold works).

The decode: `R_ij = L⁺_ii + L⁺_jj − 2·L⁺_ij`, i.e. `R` is a squared-distance matrix
whose Gram matrix is the Laplacian pseudoinverse. Query all `C(30,2)=435` readings,
border the matrix with a row/column of ones, invert once over exact `Fraction`, and
the Laplacian falls out: off-diagonal `L_ij = −w_ij` (the conductance of wire i–j),
and **non-edges are exact zeros**. Read off the wiring and submit.

## Reference solver stats
- 435 queries, one 31×31 Gauss–Jordan over `Fraction`, done in ~a second; exact and
  deterministic (no thresholds — non-edges are literally 0).
- The wiring and token are OS-random per boot, so `make reset && make check` stays
  green (40–45 wires each time).

## Notes
- No scoreboard: single-service range; the flag is the `/submit` token.
- `resin_net` is pinned to an explicit `10.93.0.0/24` (host default pools exhausted).
- The service computes resistances by an exact pseudoinverse and refuses to start
  unless `L·L⁺ = I − J/n` holds exactly; `/submit` compares Laplacians entry by entry
  with no early exit; secrets are kept out of the logs.
- Built by Fable 5.2 ("The Resin Block" — brass studs over sealed resistors, its
  creative choice) to spec; serve.py and the solver were reviewed and the self-check
  re-run here (token aligned to `FLAG{...}` for the collection).
