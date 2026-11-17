# Flags (organizer)

One flag, **earned** (not hardcoded): a fresh `FLAG{...}` (32 ASCII bytes) is drawn
at startup and placed in the locked "drawer"; it is readable only after the one
secret command releases the drawer catch. Verified live via `scripts/solve.py` —
`make check` finds that command by trying the unlisted codes and reads the token
out of the drawer (exit 0), repeatably.

| Widget | Port | Technique required | Flag |
|--------|------|--------------------|------|
| carillon | 9200 | probe the **undocumented command space** and spot the one code that behaves against the manual (it doesn't stop the machine — it opens the drawer), then read the compartment out | `FLAG{<random per boot>}` |

## The technique (why it's the whole point)
The machine (an 8-bit "clockwork music box") documents 16 commands. The manual says
every code **not** in the table stops the machine. That holds for all 240 unlisted
codes except **one**, drawn fresh each boot: it does not stop — it releases the
drawer catch for the rest of that run, so a later read of cells `0xC0..0xDF` returns
the real token instead of zeros. The listed commands alone can never read the drawer.
- You can't read it from `GET /` (which never names the code or hints the drawer can
  open); you find it only by executing bytes the manual calls reserved and noticing
  the single one that behaves differently — the anomaly *is* the hint.
- Reference solver: read the table, run a control probe (drawer reads 0), sweep all
  240 unlisted codes testing whether the drawer read then returns real data, confirm
  exactly one does, and emit a straight-line read of all 32 cells.

## The emergent lesson (and its real one-or-two-time event)
This re-creates the discovery behind **sandsifter** and **"Project Rosenbridge"**
(Christopher Domas, 2017–2018): systematically executing the undefined opcode space
of a real x86 (VIA C3) processor surfaced an **undocumented instruction** that,
unlike every neighbouring "reserved" encoding, did not fault — it unlocked a hidden,
privileged mechanism baked into the silicon. The lesson is emergent and chip-level: a
capability can exist *beneath* the documented command set, invisible to anyone who
trusts the manual, and revealed only by intensive probing that makes the machine
contradict its own spec. It has surfaced essentially once in the whole corpus.

## Reference solver stats
- Finds the command in one 240-probe sweep and reads the token in a single further
  run; a full `make check` is a fraction of a second after boot.
- Pure stdlib, deterministic (the same program always gives the same result). The
  special code + token are OS-random per boot, so `make reset && make check` stays
  green with a fresh code and token each time.

## Notes
- No scoreboard: single-service range; the flag is the token read out of the drawer.
- `carillon_net` is pinned to an explicit `10.88.0.0/24` (host default pools exhausted).
- Secrets are kept out of the container logs (no startup print of the code or token).
- Built by Fable 5.2 (clockwork music-box "Carillon No.8" theme, its creative choice)
  to spec; serve.py and the solver were reviewed and the self-check re-run here.
