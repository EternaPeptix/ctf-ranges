# treadle

A self-contained sandbox for a **hidden-machine reconstruction** puzzle.

One small HTTP service plays a loom with a secret chain of pattern cards: a
hidden deterministic **Mealy machine** with 24 to 40 states over 2 or 3 input
symbols (treadles) and 2 or 3 output symbols (dyes). It weaves any input string
you send it, one output symbol per input symbol, and it will compare a machine
you submit against its own, exactly. Whoever submits a machine that behaves
identically on every input string receives a completion token `FLAG{...}`.

There is nothing to exploit and nothing to stumble on. The only way through is
to learn the machine's structure from its answers.

## Run it

Needs Docker and `make`.

```
make up       # build + start the service -> http://localhost:8900
make check    # run the reference solver in-network; exit 0 iff the token is recovered
make down     # stop + remove
make reset    # down + up: fresh secret machine and fresh token
```

`make check` prints the solver's progress, a `TOKEN: FLAG{...}` line, and a
final `[verify] PASS` line. It takes about a second.

## Layout

```
Makefile                 up / check / down / reset
docker-compose.yml       service `app` (container trd-app), network treadle_net
app/Dockerfile           python:3.12-slim + flask==3.0.3
app/serve.py             the puzzle service (port 80 in-container, 8900 on the host)
scripts/verify.sh        runs solve.py in a throwaway container on treadle_net
scripts/solve.py         reference solver: query-only, standard library only
challenge/BRIEF.md       the puzzle as handed to a solver (no method spoilers)
organizer/SOLUTION.md    the full method (spoilers)
```

## API

| Endpoint | Body | Result |
|---|---|---|
| `GET /` | | box description: `sigma`, `gamma`, state-count range, endpoints |
| `POST /run` | `{"input": "<string over sigma>"}` | `{"output": "<string over gamma, same length>"}`, exactly `out(input)` |
| `POST /conjecture` | `{"machine": {"start": id, "states": [...], "delta": {state: {sym: next}}, "lambda": {state: {sym: out_sym}}}}` | `{"solved": true, "token": "FLAG{...}"}` or `{"solved": false, "counterexample": "<shortest differing input>"}` |

- Symbols are single characters: treadles `1`, `2` (and `3`); dyes `i` indigo,
  `m` madder (and `w` weld). `GET /` says which are in play.
- `/run` always starts from the start state. The empty input gives the empty output.
- `/conjecture` checks **exact equivalence** by breadth-first search over the
  product of the two machines, and on failure returns a shortest input on which
  the output strings differ. State ids may be strings or integers. A submitted
  machine must be complete over `sigma`, emit only symbols of `gamma`, and have
  at most 2048 states; it need not be minimal.
- `/conjecture` responses also carry a `message` string, and `GET /` a `ledger`
  of how many runs and conjectures the box has served. Both are decoration.
- Malformed requests get HTTP 400 and `{"error": "..."}`. `/run` inputs are
  capped at 8192 symbols.

## Notes

- The machine and the token are generated in memory at container start and
  are different on every start. Nothing secret is written to disk, the
  environment, or the logs. `GET /` never reveals the state count, the
  transitions, the outputs or the start state.
- The machine is generated at random, trimmed to its reachable part, minimised
  by partition refinement, and redrawn until the state count is in [24, 40].
  The service is deterministic once started: the same request always gets the
  same answer.
- The network `treadle_net` is pinned to `10.86.0.0/24`. The default Docker
  address pools on the build host are exhausted, so the explicit subnet is
  required; change it in `docker-compose.yml` if it collides on your machine.
- The solver uses no randomness and waits up to a minute for the service to
  come up, so `make reset && make check` works back to back. Override its
  target with `TREADLE_URL` (for example
  `TREADLE_URL=http://localhost:8900 python3 scripts/solve.py` from the host).
- The service runs on Flask's built-in server, which is plenty for a puzzle box
  on a private network and not meant for the open internet.
