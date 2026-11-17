# treadle -- brief

## The setting

There is a loom in the back room. Behind its cloth beam runs a closed chain of
pattern cards that nobody is allowed to look at. Each time you press a treadle
the loom throws exactly one pick of weft. Which dye comes off the shuttle
depends on the treadle you pressed and on the card that is under the needles
at that moment; the chain then advances to some other card (or stays put).
Before every piece of cloth the chain is wound back to the same starting card.

Without the wood and the wool: the service holds a hidden **deterministic
finite-state machine with outputs on its transitions** (a Mealy machine).

- Input alphabet `Sigma` (the treadles): 2 or 3 symbols.
- Output alphabet `Gamma` (the dyes): 2 or 3 symbols.
- A secret start state, a secret transition function `delta: Q x Sigma -> Q`
  and a secret output function `lambda: Q x Sigma -> Gamma`, both total.
- Between **24 and 40** states. The machine is *minimal* (no two states behave
  alike) and every state is reachable from the start. The exact count is not
  disclosed.

For an input string `s` over `Sigma`, `out(s)` is the string of output symbols
the machine emits while reading `s` from the start state: one output symbol
per input symbol, so `|out(s)| = |s|`.

The machine is fixed for as long as the service is up and is different each
time it is started. `GET /` tells you the actual `Sigma` and `Gamma`.

## The goal

**Recover the machine's behaviour exactly** and submit a machine of your own.
If your machine emits the same output as the hidden one on *every* input
string, the service returns a completion token of the form `FLAG{...}`.

You do not have to reproduce the hidden machine's own state names, or even its
state count: any machine with the same `out(.)` is accepted.

## The service

Base URL: `http://app/` on the puzzle network (`http://localhost:8900/` from the host).
All requests and responses are JSON. Symbols are single characters.

### `GET /`

Describes the box: `sigma`, `gamma`, the state-count range and the endpoints.

### `POST /run`

Weave a treadling from the start card.

```
request   {"input": "12212"}
response  {"output": "imwwi"}
```

`output` is exactly `out(input)`. The empty string gives the empty string.
Every call starts again from the start state. (The values above only
illustrate the format.)

### `POST /conjecture`

Hand in a draft: a complete machine over the same alphabets.

```
request   {"machine": {
             "start":  "a",
             "states": ["a", "b"],
             "delta":  {"a": {"1": "b", "2": "a"}, "b": {"1": "a", "2": "b"}},
             "lambda": {"a": {"1": "i", "2": "m"}, "b": {"1": "m", "2": "m"}}
          }}
response  {"solved": true,  "token": "FLAG{...}"}
     or   {"solved": false, "counterexample": "2112"}
```

- `states` lists your state identifiers (strings or integers, compared as
  strings). `start` is one of them.
- `delta[state][symbol]` is the next state and `lambda[state][symbol]` is the
  output symbol. Both must be given for every state and every symbol of `sigma`.
- The check is exact, not sampled. If your machine is not equivalent to the
  hidden one you get a `counterexample`: a shortest input string on which the
  two output strings differ.

Malformed requests get HTTP 400 and `{"error": "..."}`.

## Rules

- Query access only. The puzzle is the machine, not the container: do not
  inspect the service's process, image, or memory.
- There is no rate limit and no query budget. Both endpoints are pure: the
  same request always gets the same answer while the service is up.
- Guessing does not work. A machine with `n` states over `k` treadles and `g`
  dyes is a table of `n*k` transitions and `n*k` outputs; there are
  `(n*g)^(n*k)` such tables, which for the smallest case here is already more
  than `10^80`. There is no magic input to stumble on either: the token is
  only ever released for a machine that is right everywhere.
- A good solution is frugal: on the order of a thousand `/run` calls and about
  ten `/conjecture` calls.
