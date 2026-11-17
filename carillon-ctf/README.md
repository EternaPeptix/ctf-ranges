# carillon

A self-contained sandbox for a **discovery** puzzle about a little machine.

One small HTTP service plays Carillon No.8, a clockwork music box that runs
byte programs: four 8-bit dials, 256 cells of memory, and a documented table of
16 commands. One block of memory, the drawer, is a locked compartment holding
a token `FLAG{...}`. The puzzle is to get the box to play that token.

It is a pure puzzle about the machine. The player's whole interface is the
manual (`GET /`) and a way to run programs (`POST /run`).

## Run it

Needs Docker and `make`.

```
make up       # build + start the service -> http://localhost:9200
make check    # run the reference solver in-network; exit 0 iff the token is recovered
make down     # stop + remove
make reset    # down + up: fresh special command and fresh token
```

`make check` prints the solver's progress, a `TOKEN: FLAG{...}` line, and a
final `[verify] PASS` line. It takes a couple of seconds.

## Layout

```
Makefile                 up / check / down / reset
docker-compose.yml       service `app` (container car-app), network carillon_net
app/Dockerfile           python:3.12-slim + flask==3.0.3
app/serve.py             the puzzle service (port 80 in-container, 9200 on the host)
scripts/verify.sh        runs solve.py in a throwaway container on carillon_net
scripts/solve.py         reference solver: GET / and POST /run only, standard library only
challenge/BRIEF.md       the puzzle as handed to a solver (no method spoilers)
organizer/SOLUTION.md    the full method (spoilers)
```

## API

- `GET /` -- the manual, as JSON: dials, the command table (code, operands,
  effect for every listed command), the memory map, limits, and the two
  endpoints.
- `POST /run {"program": "<hex bytes>"}` -- runs the program on a fresh
  machine and returns
  `{"output": "<hex>", "state": {"registers", "position", "stopped", "reason"}, "steps": n}`.

```
curl -s localhost:9200/ | python3 -m json.tool
curl -s localhost:9200/run -H 'Content-Type: application/json' \
     -d '{"program":"11008020010030014f"}'
```

## Notes

- **Deterministic.** A run is a pure function of the program; every run starts
  from a fresh machine. The only randomness is what the service draws once at
  startup (see `organizer/SOLUTION.md`), so `make reset` gives a new instance
  of the puzzle and `make check` solves it again from scratch.
- **Network.** `carillon_net` is pinned to `10.88.0.0/24`, because the host's
  default Docker address pools are exhausted.
- **Dependencies.** The service is the Python standard library plus Flask
  3.0.3. The solver is standard library only and can also be run from the
  host: `CARILLON_URL=http://localhost:9200 python3 scripts/solve.py`.
- Hand players `challenge/BRIEF.md` only. `organizer/` and `scripts/solve.py`
  give the method away.
