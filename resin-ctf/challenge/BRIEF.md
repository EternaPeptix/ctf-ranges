# The Resin Block

A block of cast resin sits at `http://localhost:9600` (inside the puzzle
network: `http://app`). Thirty brass studs, numbered `0` to `29`, stick out of
it. Before the resin was poured, somebody soldered resistors between some
pairs of studs. The resin is opaque, and the block does not come apart.

An ideal ohmmeter is clipped to the bench. You may put its two probes on any
two studs, as often as you like, and it reads exactly.

**Work out the wiring: which pairs of studs are joined, and by what.**

## The network

- It is an undirected graph on the `n` studs (`GET /` gives `n`; it is 30).
- It is **connected** and **sparse**: only a small fraction of the pairs are
  wired. There is at most one wire per pair and no wire from a stud to itself.
- Each wire `{i, j}` has a **weight** `w`, a positive rational number with a
  small numerator and denominator. The weight is the *conductance* of that
  resistor: on its own, the resistor has resistance `1/w`.

## What you can measure

```
POST /resistance   {"i": a, "j": b}

-> {"resistance": "num/den"}
```

This is the **effective resistance** between studs `a` and `b`: the voltage
between them when one unit of current is fed in at `a` and drawn out at `b`,
with the whole network in place. It is what an ohmmeter shows, and it follows
the usual rules: resistances add in series, conductances add in parallel.

The reading is exact, a fraction in lowest terms (`"k/1"` for an integer). It
is symmetric in `a` and `b`, and `"0/1"` when `a = b`.

A small example, not the block: three studs wired in a triangle with weights
`w01 = 2`, `w12 = 3`, `w02 = 6`. Between 0 and 1 the current has the direct
resistor (conductance 2) and the detour through 2 (resistance `1/6 + 1/3 =
1/2`, conductance 2), so the reading is `1/(2 + 2) = 1/4`. The other two
readings are `2/9` and `5/36`.

Note what the example already shows. The reading across a wire is not `1/w`
once there is any other way round. And since the block is connected, **every**
pair of studs gives a finite reading, wired or not: a single reading does not
tell you whether two studs are joined, and a low reading does not mean a wire.

## Handing in the wiring

```
POST /submit   {"edges": [[i, j, "num/den"], ...]}

-> {"solved": true, "token": "FLAG{...}"}      the wiring is right
-> {"solved": false}                             it is not
```

One entry per wire: the two studs and the weight, as an exact fraction such as
`"7/3"` (a plain integer is fine too). Order and orientation do not matter. If
you list a pair more than once the weights are added. The answer is `solved`
only if, pair by pair, your weights equal the hidden ones exactly, and you
list nothing where there is no wire. A wrong submission tells you nothing
about what was wrong.

```
curl -s localhost:9600/ | python3 -m json.tool
curl -s localhost:9600/resistance -H 'Content-Type: application/json' -d '{"i":0,"j":1}'
curl -s localhost:9600/submit -H 'Content-Type: application/json' \
     -d '{"edges":[[0,1,"1/2"],[1,2,"3/1"]]}'
```

## Goal

Get `{"solved": true}` and the token `FLAG{...}` that comes with it.

## Ground rules

- Only `GET /`, `POST /resistance` and `POST /submit` are in play. The puzzle
  is the block itself: there is nothing to find in the web server, the
  container or the network.
- No rate limit, and no limit on the number of readings or submissions.
- The wiring and the token are drawn fresh each time the service starts.
  `GET /` carries an `instance` id that changes when that happens; readings
  from two different instances do not belong together.
