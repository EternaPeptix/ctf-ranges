# Flags (organizer)

One flag, **earned** (not hardcoded): the service mints a fresh
`FLAG{treadle_learn_hidden_mealy_machine_<random>}` at startup and reveals it from
`POST /conjecture` only to a submitted machine that is *exactly* equivalent to the
hidden one. Verified live via `scripts/solve.py` — `make check` reconstructs the
machine from `/run` + `/conjecture` alone and recovers the token (exit 0), repeatably.

| Widget | Port | Technique required | Flag |
|--------|------|--------------------|------|
| treadle | 8900 | active automata learning — Angluin's **L\*** (Mealy variant) with Rivest–Schapire counterexample analysis | `FLAG{treadle_learn_hidden_mealy_machine_<random per boot>}` |

## The technique (why it's the whole point)
The hidden object is a minimal, fully-reachable **Mealy machine** of 24–40 states
over a 2–3 symbol input alphabet. You get exactly two queries:
- `POST /run` — the output string for an input (a *membership/output* query), and
- `POST /conjecture` — submit a machine; the service either accepts it (returns the
  token) or returns a **shortest counterexample** input (the *equivalence teacher*).

This is the classic MAT (minimally adequate teacher) setup, and L\* is the intended
(and essentially required) method: a 24–40-state transition table cannot be guessed,
and no amount of random fuzzing finds a distinguishing structure. The solver builds
an observation table, drives it to closed + consistent, conjectures the induced
machine, and folds each counterexample back in via Rivest–Schapire binary search —
converging in ~5–10 conjectures and a few hundred `/run` queries.

This technique maps to **model learning / protocol state-machine fuzzing** — a real
method that is effectively absent from public bug-bounty writeups (near-zero signal
if you scrape H1/Bugcrowd/Intigriti/GitHub); the challenge is deliberately a pure
hidden-machine reconstruction puzzle.

## Reference solver stats
- Recovers the exact machine, typically in 5–10 conjectures and ~120–920 `/run`
  queries; a full `make check` run is well under a second.
- Pure stdlib, no randomness — a run is a deterministic function of the box. The
  service's secret machine + token are OS-random per boot, so `make reset && make
  check` stays green. (Offline: 1000/1000 random machines reconstructed.)

## Notes
- No scoreboard: single-service range; the flag is the `/conjecture` token.
- The host's default Docker address pools are exhausted by sibling ranges, so the
  compose pins `treadle_net` to an explicit `10.86.0.0/24`.
- Built by Fable 5.2 (loom theme, its creative choice) to spec; the organizer
  self-check, generator, and exact equivalence teacher were reviewed and re-run here
  (token format aligned to `FLAG{...}` for the collection).
