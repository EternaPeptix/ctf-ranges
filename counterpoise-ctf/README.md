# counterpoise

A self-contained sandbox for a **combinatorics** puzzle about asking few
questions.

One small HTTP service hides a bit vector `x` in `{0,1}^1024`, dressed up as a
wall of 1024 sealed tins that each hold one brass slug or nothing. The only
instrument is a two-pan balance: name some tins for the left pan and some
others for the right, and it reports (slugs on the left) minus (slugs on the
right). The balance gives **255 readings in total** and then refuses. Submit
the full vector to receive a token `FLAG{...}`.

Reading the tins one at a time would take 1024 questions, so the 255 have to
be designed.

## Run it

Needs Docker and `make`.

```
make up       # build + start the service -> http://localhost:9300
make check    # run the reference solver in-network; exit 0 iff the token is recovered
make down     # stop + remove
make reset    # down + up: fresh hidden vector and fresh token
```

`make check` prints the solver's progress, a `TOKEN: FLAG{...}` line, and a
final `[verify] PASS` line. It takes about a second and also leaves the
solver output in `verify.log`.

## Layout

```
Makefile                 up / check / down / reset
docker-compose.yml       service `app` (container cp-app), network counterpoise_net
app/Dockerfile           python:3.12-slim + flask==3.0.3
app/serve.py             the puzzle service (port 80 in-container, 9300 on the host)
scripts/verify.sh        runs solve.py in a throwaway container on counterpoise_net
scripts/solve.py         reference solver: GET /, POST /weigh, POST /submit; standard library only
challenge/BRIEF.md       the puzzle as handed to a solver (no method spoilers)
organizer/SOLUTION.md    the full method (spoilers)
```

## API

- `GET /` -- the instruction card, as JSON: `n` (1024), `budget` (255),
  `asked`, `remaining`, the query rule and the endpoints. Never the vector.
- `POST /weigh {"plus":[...], "minus":[...]}` -- `plus` and `minus` are
  disjoint, repeat-free lists of indices `0..1023`, so each index gets a
  coefficient of `+1`, `-1` or `0`. Returns
  `{"result": (# ones among plus) - (# ones among minus), "asked": k, "remaining": 255 - k}`.
  Each answered call costs one question; once 255 are used the answer is
  `429` and no result.
- `POST /submit {"bits":"<1024 chars of 0/1>"}` -- returns
  `{"solved":true,"token":"FLAG{...}"}` if it equals the vector, else
  `{"solved":false}`.

```
curl -s localhost:9300/ | python3 -m json.tool
curl -s localhost:9300/weigh -H 'Content-Type: application/json' \
     -d '{"plus":[0,1,2],"minus":[10,11]}'        # spends one of the 255
```

## Notes

- **The budget is real.** The count is kept server-side under a lock, per
  hidden vector, across all clients and connections; parallel requests cannot
  get a 256th answer. A malformed question (overlapping pans, a repeated or
  out-of-range index, a missing field) is rejected with `400` and is not
  charged. The reference solver uses exactly 255, so any stray question
  against a wall (a test `curl`, for instance) leaves it one short: run
  `make reset` before `make check` in that case. The solver notices and says
  so rather than spending what is left.
- **A solved box restocks itself.** After a correct submission the service
  draws a new hidden vector and sets the counter back to 0; the token stays
  the one set at startup. That is why `make check` can be run again and again
  without a reset. Nothing else returns questions: an unsolved vector whose
  budget is gone stays that way until `make reset`.
- **Deterministic.** The solver has no randomness: the same 255 questions
  every run, and an exact decoder. The only randomness is what the service
  draws (`secrets`): the vector and the token at startup, and a new vector
  after each solve. Neither is ever logged.
- **Network.** `counterpoise_net` is pinned to `10.90.0.0/24`, because the
  host's default Docker address pools are exhausted.
- **Dependencies.** The service is the Python standard library plus Flask
  3.0.3. The solver is standard library only and can also be run from the
  host: `COUNTERPOISE_URL=http://localhost:9300 python3 scripts/solve.py`.
- Hand players `challenge/BRIEF.md` only. `organizer/` and `scripts/solve.py`
  give the method away.
