# quorum

A self-contained sandbox for a **number-theory** puzzle.

One small HTTP service plays a bench of 250 witnesses guarding one sealed
integer `N` of about 2000 bits. Each witness holds a distinct 20-bit prime
`p_i` and, when asked, states `N mod p_i`. At most 70 of the witnesses are
**liars**: a liar states one fixed wrong remainder, the same on every query,
and nothing says which witnesses they are. Whoever submits `N` receives a
completion token `FLAG{...}`.

There is nothing to exploit in the service and nothing to stumble on. Plain
Chinese remaindering over all the answers returns garbage, and guessing a
liar-free subset is hopeless (about `2^-67` per try). The way in is arithmetic
on what the witnesses state.

## Run it

Needs Docker and `make`.

```
make up       # build + start the service -> http://localhost:9400
make check    # run the reference solver in-network; exit 0 iff the token is recovered
make down     # stop + remove
make reset    # down + up: fresh primes, fresh N, fresh liars, fresh token
```

`make check` prints the solver's progress, a `TOKEN: FLAG{...}` line, and a
final `[verify] PASS` line. It takes about a second, plus the wait for the
service if it has only just been started.

## Layout

```
Makefile                 up / check / down / reset
docker-compose.yml       service `app` (container qrm-app), network quorum_net
app/Dockerfile           python:3.12-slim + flask==3.0.3
app/serve.py             the puzzle service (port 80 in-container, 9400 on the host)
scripts/verify.sh        runs solve.py in a throwaway container on quorum_net
scripts/solve.py         reference solver: standard library only
challenge/BRIEF.md       the puzzle as handed to a solver (no method spoilers)
organizer/SOLUTION.md    the full method and the parameter inequality (spoilers)
```

## API

| Endpoint | Body | Result |
|---|---|---|
| `GET /` | | the rules: `primes` (250 integers), `bound` (decimal string, `2^2000`), `bound_bits`, `max_liars` (70), `M`, `prime_bits`, `endpoints`, plus `name` and `about` |
| `POST /residue` | `{"i": <index>}` | `{"residue": <integer>}`: `N mod primes[i]` for an honest index, the liar's fixed wrong value otherwise |
| `POST /submit` | `{"N": "<decimal integer>"}` | `{"solved": true, "token": "FLAG{...}"}` if the integer is `N`, else `{"solved": false}` |

- `i` must be a JSON integer with `0 <= i < 250`. Anything else gets HTTP 400
  and `{"error": "..."}`.
- The same index always returns the same residue, honest or not.
- `/submit` takes `N` as a decimal string (a JSON integer is accepted too). It
  must be `N` itself. Malformed requests get HTTP 400 and
  `{"solved": false, "error": "..."}`.
- Bodies over 16 KiB get HTTP 413. Unknown paths and wrong methods get a JSON
  `{"error": "..."}` with the matching status.
- No endpoint ever reveals `N` or which indices lie. There is no rate limit
  and no query budget.

## Notes

- Everything is drawn from the operating system's random source at container
  start and is different on every start: the 250 primes, `N`, the liar set,
  each liar's wrong residue, and the token. Nothing secret is written to disk,
  the environment, or the logs.
- The service is deterministic once started. `GET /` is serialised once at
  boot and returns the same bytes every time; `/residue` and `/submit` give
  the same answer to the same request.
- Primes come from a Miller-Rabin test written against the standard library
  (`app/serve.py`, `is_prime`; bases 2, 3, 5, 7, which is exact for 20-bit
  numbers).
- Before it listens, the service audits its own draw and checks that recovery
  is guaranteed in the worst case, `2 * B * Emax^2 < Mprod` with `Emax` the
  product of the 70 largest primes (`recovery_check` in `app/serve.py`; the
  result is printed to the container log). It exits rather than serve a box
  that fails. For 250 distinct 20-bit primes the inequality cannot fail; see
  `organizer/SOLUTION.md`.
- Boot is immediate. The solver still waits up to two minutes for the service,
  so `make reset && make check` works back to back.
- The network `quorum_net` is pinned to `10.91.0.0/24`. The default Docker
  address pools on the build host are exhausted, so the explicit subnet is
  required; change it in `docker-compose.yml` if it collides on your machine.
- The solver uses no randomness and no search. Override its target with
  `QUORUM_URL` (for example
  `QUORUM_URL=http://localhost:9400 python3 scripts/solve.py` from the host;
  it needs Python 3.8 or later).
- `scripts/verify.sh` keeps the solver output of the last run in `verify.log`
  at the top of this directory (gitignored).
- The service runs on Flask's built-in server, which is plenty for a puzzle
  box on a private network and not meant for the open internet.
