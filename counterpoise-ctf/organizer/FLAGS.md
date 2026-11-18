# Flags (organizer)

One flag, **earned** (not hardcoded): a `FLAG{...}` set at startup is returned by
`POST /submit` only to the exact hidden bit vector. Verified live via
`scripts/solve.py` — `make check` recovers all 1024 bits within the 255-question
budget and gets the token (exit 0), repeatably.

| Widget | Port | Technique required | Flag |
|--------|------|--------------------|------|
| counterpoise | 9300 | non-adaptive **measurement design** — a Cantor–Mills detecting matrix (coin-weighing) | `FLAG{<random per boot>}` |

## The technique (why it's the whole point)
A hidden vector `x ∈ {0,1}^1024`; the only instrument is a signed count
`(#ones in plus) − (#ones in minus)` over disjoint, repeat-free index sets, with a
hard budget of **255** questions. Reading one bit per question needs 1024; clever
small gadgets stall around n/4. So you cannot adapt your way out — you must **design
all 255 measurements up front**.

The construction is a Cantor–Mills **detecting matrix**: `D_1=[1]`,
`D_{k+1} = [[D,D,I,0],[D,−D,0,0],[0,0,0,1]]`. `D_8` has exactly `2^8−1 = 255` rows and
`8·2^7 = 1024` columns; each row is a ±1 question. Fire all 255, then decode
recursively: the middle block gives `D(x−y)`, the top gives `D(x+y)+z`, and since
`D(x+y) ≡ D(x−y) (mod 2)` you read `z` off by parity, then `Dx`, `Dy` by
half-sum/half-difference, and recurse. *The aha: the parity of `D(x+y)` is already
known from `D(x−y)`, so every sum-row smuggles one extra bit for free.*

## Reference solver stats
- Fully **non-adaptive**: it emits all 255 questions before reading any answer, then
  decodes deterministically (~40 lines) and checks the decoded bits reproduce all 255
  readings before submitting. A `make check` run is ~0.6 s.
- The vector and token are OS-random per boot. The 255-budget is strict per vector; a
  correct submit releases the (boot-fixed) token and **restocks a fresh vector with a
  zeroed counter**, so `make check` is repeatable without a reset. No vector ever gets
  more than 255 answered questions.

## Notes
- No scoreboard: single-service range; the flag is the `/submit` token.
- `counterpoise_net` is pinned to an explicit `10.90.0.0/24` (host default pools exhausted).
- Malformed `/weigh` calls return 400 and are **not** charged; the budget is enforced
  under a lock (concurrency-tested: 255 answered, the rest refused); secrets are never
  logged. `challenge/BRIEF.md` includes a paper-only ladder (4 bits in 3, 12 in 7, …) as
  a hint toward the recursion.
- Built by Fable 5.2 ("Counterpoise" — 1024 sealed tins and a two-pan balance, its
  creative choice) to spec; serve.py and the solver were reviewed and the self-check
  re-run here (token aligned to `FLAG{...}` for the collection; the restock-on-solve is
  kept so the self-check repeats).
