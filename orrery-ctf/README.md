# orrery

A self-contained sandbox for a **sparse-polynomial reconstruction** puzzle.

One small HTTP service plays a brass orrery with six arms and a hidden gear
train: a secret **sparse polynomial `f` in 6 variables over a prime field
`F_p`** (`p` a fixed 301-bit prime). `f` has at most 16 terms and every
exponent is in `0..20`; how many terms there are, which exponents and which
coefficients are all secret. The service will evaluate `f` at any point you
choose, but only **32 times per startup**, and it will compare a polynomial you
submit against its own, exactly. Whoever submits `f` receives a completion
token `FLAG{...}`.

There is nothing to exploit and nothing to stumble on. The only way through is
to choose the 32 evaluation points well and do the algebra.

## Run it

Needs Docker (with Compose v2) and `make`.

```
make up       # build + start the service -> http://localhost:9500
make check    # fresh instance + reference solver in-network; exit 0 iff the token is recovered
make down     # stop + remove
make reset    # down + up: fresh polynomial, fresh token, full budget
```

`make check` prints the solver's progress, a `TOKEN: FLAG{...}` line and a
final `[verify] PASS` line. It takes a few seconds, nearly all of it Docker.

Because the reference solver spends the whole evaluation budget, a correct
submission **winds a fresh gear train with a full budget** — a new polynomial,
with the token fixed at startup. So `make check` is a plain `scripts/verify.sh`
(like the sibling boxes) and stays green however often it is run. The budget is
strict per gear train: no polynomial is ever answered more than 32 times.

## Layout

```
Makefile                 up / check / down / reset
docker-compose.yml       service `app` (container orr-app), network orrery_net (10.92.0.0/24)
app/Dockerfile           python:3.12-slim + flask==3.0.3
app/serve.py             the puzzle service (port 80 in-container, 9500 on the host)
scripts/verify.sh        runs solve.py in a throwaway container on orrery_net, logs to verify.log
scripts/solve.py         reference solver: 32 evaluations, standard library only
challenge/BRIEF.md       the puzzle as handed to a solver (no method spoilers)
organizer/SOLUTION.md    the full method (spoilers)
```

## API

| Endpoint | Body | Result |
|---|---|---|
| `GET /` | | box description: `p`, `variables`, `max_degree_per_variable`, `max_terms`, `budget` (`evaluations`, `used`, `remaining`), endpoints |
| `POST /eval` | `{"x": [v0, v1, v2, v3, v4, v5]}` | `{"y": f(x) mod p}`; costs one of the 32 evaluations |
| `POST /submit` | `{"terms": [[e0, e1, e2, e3, e4, e5, coeff], ...]}` | `{"solved": true, "token": "FLAG{...}"}` if the terms are exactly `f`, else `{"solved": false}` |

- All numbers are plain JSON integers. `/eval` inputs and `/submit` coefficients
  may be any integers and are reduced mod `p`; `y` is in `0..p-1`.
- **Budget.** Every answered `/eval` costs one evaluation, repeats of an earlier
  point included. After 32 the endpoint answers HTTP 429 until the service is
  restarted. Each answer carries an `X-Evaluations-Remaining` header and `GET /`
  shows the running count. Malformed requests (HTTP 400) cost nothing.
- **Submission.** The check is equality of polynomials: like terms are combined,
  zero coefficients dropped, term order ignored. Exponents must be non-negative
  integers (anything above 20 simply cannot match). A submission may list at
  most 256 terms. `/submit` is free and unlimited, and a wrong answer gets
  nothing but `{"solved": false}`.
- Malformed requests get HTTP 400 and an `error` string (on `/submit` together
  with `"solved": false`). Request bodies are capped at 64 KiB.

## Notes

- The polynomial and the token are drawn from the OS random source at container
  start and are different on every start. The term count is uniform in 8..16
  (the floor is not advertised), the exponent vectors are distinct and uniform
  in `{0..20}^6`, the coefficients uniform in `1..p-1`. Nothing secret is
  written to disk, the environment or the logs, and `GET /` never reveals the
  term count, the exponents or the coefficients.
- `p = 2^300 + 157`, the first prime above `2^300`. The service checks at
  startup that it is prime and large enough for the puzzle to be well posed.
- The network `orrery_net` is pinned to `10.92.0.0/24`. The default Docker
  address pools on the build host are exhausted, so the explicit subnet is
  required; change it in `docker-compose.yml` if it collides on your machine.
- The solver is deterministic (its one randomised step uses a fixed seed), never
  retries a paid request, and waits up to a minute for the service to come up.
  Override its target with `ORRERY_URL` (for example
  `ORRERY_URL=http://localhost:9500 python3 scripts/solve.py` from the host).
- The service runs on Flask's built-in server, which is plenty for a puzzle box
  on a private network and not meant for the open internet.
