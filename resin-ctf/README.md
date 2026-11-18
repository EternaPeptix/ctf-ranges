# resin

A self-contained sandbox for a **graph-inference** puzzle.

One small HTTP service plays the Resin Block: thirty brass studs on a block of
cast resin, with a web of resistors sealed inside. That web is a connected,
sparse, weighted undirected graph, drawn fresh at startup. The only thing a
player can ask is the exact effective resistance between two studs. The puzzle
is to hand back the wiring, weights included; a correct answer returns a token
`FLAG{...}`.

## Run it

Needs Docker and `make`.

```
make up       # build + start the service -> http://localhost:9600
make check    # run the reference solver in-network; exit 0 iff the token is recovered
make down     # stop + remove
make reset    # down + up: fresh wiring and fresh token
```

`make check` prints the solver's progress, a `TOKEN: FLAG{...}` line, and a
final `[verify] PASS` line. It takes about a second. The run is also kept in
`verify.log`.

## Layout

```
Makefile                 up / check / down / reset
docker-compose.yml       service `app` (container rsn-app), network resin_net
app/Dockerfile           python:3.12-slim + flask==3.0.3
app/serve.py             the puzzle service (port 80 in-container, 9600 on the host)
scripts/verify.sh        runs solve.py in a throwaway container on resin_net
scripts/solve.py         reference solver: the three public endpoints, standard library only
challenge/BRIEF.md       the puzzle as handed to a solver (no method spoilers)
organizer/SOLUTION.md    the full method (spoilers)
```

## API

- `GET /` -- the manual, as JSON: `n`, how the studs are labelled, what a
  weight and a reading mean, and the endpoints. It never contains the wiring.
- `POST /resistance {"i": a, "j": b}` -- `{"resistance": "num/den"}`, the
  exact effective resistance between studs `a` and `b`, in lowest terms.
- `POST /submit {"edges": [[i, j, "w_num/w_den"], ...]}` --
  `{"solved": true, "token": "FLAG{...}"}` if the submitted weighted graph
  is the hidden one, else `{"solved": false}`.

```
curl -s localhost:9600/ | python3 -m json.tool
curl -s localhost:9600/resistance -H 'Content-Type: application/json' -d '{"i":0,"j":1}'
curl -s localhost:9600/submit -H 'Content-Type: application/json' \
     -d '{"edges":[[0,1,"1/2"],[1,2,"3/1"]]}'
```

## Notes

- **Deterministic.** Every answer is a pure function of the request and of
  what the service drew at startup (the wiring and the token, from the OS
  random source). All arithmetic is exact (`fractions.Fraction`) on both
  sides, so there is no tolerance anywhere. `make reset` gives a new instance
  and `make check` solves it again from scratch.
- **Network.** `resin_net` is pinned to `10.93.0.0/24`, because the host's
  default Docker address pools are exhausted.
- **Dependencies.** The service is the Python standard library plus Flask
  3.0.3. The solver is standard library only and can also be run from the
  host: `RESIN_URL=http://localhost:9600 python3 scripts/solve.py`.
- **Logs.** The service prints one startup line. It never logs the wiring or
  the token, and per-request logging is off.
- Hand players `challenge/BRIEF.md` only. `organizer/` and `scripts/solve.py`
  give the method away.
