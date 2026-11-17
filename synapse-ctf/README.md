# synapse

A self-contained sandbox for a pure-math **function-reconstruction** puzzle.

One small HTTP service holds a hidden piecewise-linear function `f: Q^6 -> Q`
(a one-hidden-layer ReLU network, 10 hidden units, secret integer parameters).
It answers exact evaluation queries. Whoever submits a function that is
*exactly* equal to `f` receives a completion token `FLAG{...}`.

Everything is exact rational arithmetic (`fractions.Fraction`). There is no
floating point anywhere, in the service or in the solver.

## Run it

Needs Docker and `make`.

```
make up       # build + start the service -> http://localhost:8800
make check    # run the reference solver in-network; exit 0 iff the token is recovered
make down     # stop + remove
make reset    # down + up: fresh secret function and fresh token
```

`make check` prints the solver's progress, the token, and a final
`[verify] PASS` line.

## Layout

```
Makefile                 up / check / down / reset
docker-compose.yml       service `app` (container syn-app), network synapse_net
app/Dockerfile           python:3.12-slim + flask==3.0.3
app/serve.py             the puzzle service (port 80 in-container, 8800 on the host)
scripts/verify.sh        runs solve.py in a throwaway container on synapse_net
scripts/solve.py         reference solver: query-only, exact, standard library only
challenge/BRIEF.md       the puzzle as handed to a solver (no method spoilers)
organizer/SOLUTION.md    the full method (spoilers)
```

## API

| Endpoint | Body | Result |
|---|---|---|
| `GET /` | | puzzle description: `n`, `H`, domain, endpoints |
| `POST /eval` | `{"x": ["p/q", ...]}` (6 coordinates) | `{"y": "num/den"}`, exactly `f(x)` |
| `POST /verify` | `{"relus": [{"q": [...], "r": "p/q", "p": "p/q"}, ...], "lin": [...], "const": "p/q"}` | `{"solved": true, "token": "FLAG{...}"}` or `{"solved": false, "mismatches": N}` |

Numbers are JSON integers or `"p/q"` strings. JSON floats are rejected.
`/verify` compares the submission `g(x) = sum_k p_k max(0, q_k.x + r_k) + lin.x + const`
with `f` on 400 fresh random rational points per call: 200 spread over boxes of
several sizes and 200 placed right next to the kink surfaces of `f`, on both sides.

## Notes

- The function and the token are generated in memory at container start and
  are different on every start. Nothing secret is written to disk, the
  environment, or the logs.
- The network `synapse_net` is pinned to `10.85.0.0/24`. The default Docker
  address pools on the build host are exhausted, so the explicit subnet is
  required; change it in `docker-compose.yml` if it collides on your machine.
- The solver's own randomness is a fixed-seed `random.Random` used for integer
  draws only, so a run is reproducible against a given instance. Override the
  seed with `SYN_SEED`, or the target with `SYN_URL` (for example
  `SYN_URL=http://localhost:8800 python3 scripts/solve.py` from the host).
