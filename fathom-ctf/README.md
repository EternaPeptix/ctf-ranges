# fathom

A self-contained sandbox for a **number puzzle**: name a hidden polynomial
from the digits of one of its roots.

One small HTTP service hides an irreducible integer polynomial `P` of degree 6
with coefficients `|ci| <= 100000`, drawn fresh at startup. Its largest real
root, `alpha`, is the reading on a gauge. A player may ask for digits of
`alpha`, as many as they like and every one exact, and nothing else. Submit
the seven coefficients of `P` and the service returns a token `FLAG{...}`.

There are about `1.28 * 10^37` candidate polynomials and no numeric fit lands
on exact integers, so neither guessing nor least squares gets anywhere. The
intended method is in `organizer/SOLUTION.md` (spoilers); `challenge/BRIEF.md`
is the spoiler-free statement handed to a solver.

## Run it

Needs Docker and `make`.

```
make up       # build + start the service -> http://localhost:9700
make check    # run the reference solver in-network; exit 0 iff the token is recovered
make down     # stop + remove
make reset    # down + up: fresh polynomial and fresh token
```

`make check` prints the solver's progress, a `TOKEN: FLAG{...}` line and a
final `[verify] PASS` line, and takes about a second. Because the solver
recovers `P` from scratch every run, `make reset && make check` stays green.

## Layout

```
Makefile                 up / check / down / reset
docker-compose.yml       service `app` (container fth-app), network fathom_net 10.94.0.0/24
app/Dockerfile           python:3.12-slim + flask==3.0.3
app/serve.py             the puzzle service (port 80 in-container, 9700 on the host)
scripts/verify.sh        runs solve.py in a throwaway python:3.12-slim container on fathom_net
scripts/solve.py         reference solver: HTTP API only, standard library only
challenge/BRIEF.md       the puzzle as handed to a solver (no method spoilers)
organizer/SOLUTION.md    the full method, including how many digits suffice (spoilers)
```

## API

- `GET /` -- JSON: the degree (6), the coefficient height bound (100000), the
  normalization of `P`, the endpoints and the digit limit. Never `P` itself.
- `POST /digits {"n": k}` with `0 <= k <= 1000` -- returns
  `{"n": k, "digits": floor(alpha * 10^k), "digits_str": "<same, as a string>"}`.
  `digits` is an exact JSON integer, correct to all `k` places (floor, toward
  minus infinity; negative if `alpha` is negative).
- `POST /submit {"coeffs": [c0, c1, c2, c3, c4, c5, c6]}` -- returns
  `{"solved": true, "token": "FLAG{...}"}` if these are exactly the
  coefficients of `P`, else `{"solved": false}`.

**Canonical normalization of `P`:** constant term first, primitive
(`gcd(c0..c6) = 1`), leading coefficient `c6 > 0`. `-P` and multiples of `P`
are not accepted.

Malformed requests get HTTP 400 with `{"error": "..."}`.

```
curl -s localhost:9700/ | python3 -m json.tool
curl -s -X POST localhost:9700/digits -H 'Content-Type: application/json' -d '{"n": 30}'
curl -s -X POST localhost:9700/submit -H 'Content-Type: application/json' \
     -d '{"coeffs": [1, 2, 3, 4, 5, 6, 7]}'
```

## How the secret is made

At startup `app/serve.py` draws `c0..c6` uniformly from `[-100000, 100000]`
with the system random source, flips the sign so `c6 > 0`, and keeps the draw
only if it is primitive, provably irreducible over Q (factor-degree patterns
modulo small primes) and has a real root (exact Sturm count). The same Sturm
chain isolates the largest real root `alpha` from the others.

Digits are then exact by construction: `floor(alpha * 10^k)` is found by
integer bisection on the exact sign of `10^(6k) * P(m / 10^k)`, an integer.
The service never holds `alpha` as a float. `P` and the token are never sent
or logged.

## Notes

- Everything is standard library plus Flask; the solver is standard library
  only and uses exact integer arithmetic, so its result does not depend on
  the platform. Nothing reaches outside the puzzle network at run time (the
  image build pulls `python:3.12-slim` and `flask==3.0.3`).
- The service runs on Flask's built-in server, which is fine for a
  single-player box and not meant for the open internet.
- `n` is capped at 1000 digits per request. The reference solver uses 120,
  plus 160 for its final check.
- Host port 9700 and subnet 10.94.0.0/24 are fixed in `docker-compose.yml`.
  The subnet is pinned because the host's default Docker address pools are
  exhausted.
- To point the solver somewhere else: `FATHOM_URL=http://localhost:9700
  python3 scripts/solve.py`.
