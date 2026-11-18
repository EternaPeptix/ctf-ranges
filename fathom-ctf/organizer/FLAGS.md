# Flags (organizer)

One flag, **earned** (not hardcoded): a fresh `FLAG{...}` set at startup is returned
by `POST /submit` only to the exact hidden polynomial. Verified live via
`scripts/solve.py` — `make check` recovers the polynomial from digits of its root and
gets the token (exit 0), repeatably across resets.

| Widget | Port | Technique required | Flag |
|--------|------|--------------------|------|
| fathom | 9700 | integer **LLL lattice reduction** — recover a polynomial from an approximation of its root | `FLAG{<random per boot>}` |

## The technique (why it's the whole point)
A hidden irreducible degree-6 integer polynomial `P` (`|cᵢ| ≤ 10⁵`); the only query is
"give me `floor(α·10ⁿ)`", digits of its largest real root `α`. There are ~10³⁷
candidate polynomials and no numeric fit yields exact integers — brute force and
least-squares both fail.

The decode: ask for ~120 digits of `α`, then build the lattice with rows
`(round(10⁸⁰·αⁱ), eᵢ)` for `i=0..6`. The shortest vector LLL returns has its `eᵢ`
part equal to the coefficient vector of `P` — *enough digits of a number are its
defining equation.* Verify the candidate against extra digits (a sign change across
the reading), the height bound, and irreducibility, then submit.

## Reference solver stats
- Reads 120 digits, runs an **exact integer LLL** (pure Python) on the 7×8 basis
  (~80–110-digit entries) in a few ms, checks the candidate, and submits. Deterministic.
  Offline: 2700/2700 random + edge-case recoveries; the first LLL vector was ±P every time.
- `P` and the token are OS-random per boot, so `make reset && make check` stays green
  (positive and negative roots both occur).

## Notes
- No scoreboard: single-service range; the flag is the `/submit` token.
- `fathom_net` is pinned to an explicit `10.94.0.0/24` (host default pools exhausted).
- The service holds `P` exactly and never as a float: it answers each digit request by
  **integer bisection on the exact sign of P**, using a rational isolator `lo` (between
  the second-largest root and `α`) found once with a **Sturm chain**. Secrets are never
  logged. `/submit` requires the canonical form (primitive, `c₆>0`), so `−P` and
  multiples are rejected.
- Built by Fable 5.2 (a "sounding line over a trench" theme, its creative choice) to
  spec; serve.py and the solver were reviewed and the self-check re-run here (token
  aligned to `FLAG{...}` for the collection).
