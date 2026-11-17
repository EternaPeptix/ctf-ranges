# mintmark

A self-contained sandbox for a **number-theory** puzzle.

One small HTTP service plays the strongroom of an old mint. It publishes a
register of 128 large composite integers (the *mintmarks* on 128 sealed
coffers), each the product of two secret 512-bit primes. One entry is the
**vault**: the service also publishes a public exponent `e = 65537` and a
sealed value `c = m^e mod V` for a secret integer `m`. Whoever submits `m`
receives a completion token `FLAG{...}`.

There is nothing to exploit in the service and nothing to stumble on. The
vault's number is a sound 1024-bit modulus when looked at alone. The way in
is arithmetic on what the register publishes.

## Run it

Needs Docker and `make`.

```
make up       # build + start the service -> http://localhost:9100
make check    # run the reference solver in-network; exit 0 iff the token is recovered
make down     # stop + remove
make reset    # down + up: fresh register, fresh sealed value, fresh token
```

`make check` prints the solver's progress, a `TOKEN: FLAG{...}` line, and a
final `[verify] PASS` line. It takes about a second, plus the wait for the
service if it has only just been started.

## Layout

```
Makefile                 up / check / down / reset
docker-compose.yml       service `app` (container mm-app), network mintmark_net
app/Dockerfile           python:3.12-slim + flask==3.0.3
app/serve.py             the puzzle service (port 80 in-container, 9100 on the host)
scripts/verify.sh        runs solve.py in a throwaway container on mintmark_net
scripts/solve.py         reference solver: standard library only
challenge/BRIEF.md       the puzzle as handed to a solver (no method spoilers)
organizer/SOLUTION.md    the full method (spoilers)
```

## API

| Endpoint | Body | Result |
|---|---|---|
| `GET /` | | the register: `directory` (128 decimal strings), `v`, `e`, `c` (decimal string), `N`, `bits`, `endpoints`, plus `name` and `about` |
| `POST /open` | `{"message": "<decimal or 0x-hex integer>"}` | `{"opened": true, "token": "FLAG{...}"}` if the integer is `m`, else `{"opened": false}` |

- `directory[i]` is the composite `V_i`; `directory[v]` is the vault.
- `bits` is `{"prime": 512, "composite": 1024}`. Every entry has exactly 1024 bits.
- `/open` takes the integer as a decimal string, a `0x`-prefixed hex string,
  or a JSON integer. It must be `m` itself (`0 < m < V`), not a number
  congruent to it.
- Malformed `/open` requests get HTTP 400 and `{"opened": false, "error": "..."}`.
  Bodies over 16 KiB get HTTP 413. Unknown paths and wrong methods get a JSON
  `{"error": "..."}` with the matching status.
- `GET /` never reveals a prime, `m`, the token, or anything about the other
  entries beyond their values.

## Notes

- Everything secret (255 primes, the layout of the register, `m`, the token)
  is drawn from the operating system's random source at container start and
  is different on every start. Nothing secret is written to disk, the
  environment, or the logs.
- The service is deterministic once started. `GET /` is serialised once at
  boot and returns the same bytes every time; `/open` gives the same answer to
  the same request.
- Primes come from a Miller-Rabin test written against the standard library
  (`app/serve.py`, `is_probable_prime`). No cryptography package is involved.
- Before it listens, the service audits its own register and then solves its
  own puzzle from the public values (`audit()` in `app/serve.py`). If any
  check fails the process exits and Docker restarts it with a new draw.
- Boot takes 2 to 3 seconds on a multi-core host, where the primes are drawn
  in worker processes, and about 8 seconds on a single core. The solver waits
  up to two minutes for the service, so `make reset && make check` works back
  to back.
- The network `mintmark_net` is pinned to `10.87.0.0/24`. The default Docker
  address pools on the build host are exhausted, so the explicit subnet is
  required; change it in `docker-compose.yml` if it collides on your machine.
- The solver uses no randomness. Override its target with `MINTMARK_URL` (for
  example `MINTMARK_URL=http://localhost:9100 python3 scripts/solve.py` from
  the host; it needs Python 3.8 or later).
- The service runs on Flask's built-in server, which is plenty for a puzzle
  box on a private network and not meant for the open internet.
