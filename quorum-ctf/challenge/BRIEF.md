# quorum -- brief

## The setting

A sealed number is kept by a bench of 250 witnesses. Nobody on the bench knows
the number. Each witness was given one prime of their own and remembers a
single thing: the remainder the sealed number leaves when divided by that
prime. Ask a witness and they will state their remainder.

Not all of them can be trusted. Up to 70 of the witnesses are liars. A liar is
not erratic: they settled on one wrong remainder long ago and state that same
wrong remainder every time they are asked. From the outside a liar looks
exactly like an honest witness.

Without the bench: the service hides one positive integer and publishes a list
of primes.

- A secret integer `N` with `0 < N < B`, where `B = 2^2000`. `N` has about
  2000 bits.
- `M = 250` distinct primes `p_0, p_1, ..., p_249`, each of 20 bits. The list
  is public.
- For every index `i` the service will state a residue. For an **honest**
  index that residue is `N mod p_i`. For a **liar** index it is some fixed
  value in `0..p_i - 1` that is **not** `N mod p_i`.
- **At most 70** of the 250 indices are liars. Which ones is secret.

Everything is drawn fresh when the service starts and stays fixed for as long
as it is up.

## The goal

**Recover `N`** and submit it. The service answers with a completion token of
the form `FLAG{...}`.

## The service

Base URL: `http://app/` on the puzzle network (`http://localhost:9400/` from the host).
All requests and responses are JSON.

### `GET /`

The rules.

```
{
  "name": "quorum",
  "about": "...",
  "M": 250,
  "prime_bits": 20,
  "bound_bits": 2000,
  "bound": "1148130695...",
  "max_liars": 70,
  "endpoints": {...},
  "primes": [524453, 525013, ...]
}
```

`primes[i]` is `p_i`. `bound` is `B = 2^2000` as a decimal string. `max_liars`
is the promise: no more than that many indices lie. (The values above only
illustrate the format.) The response is the same every time you ask.

### `POST /residue`

```
{"i": 17}
```

`i` is an integer index, `0 <= i < 250`. The answer is

```
{"residue": 401337}
```

the residue stated for index `i`: `N mod p_i` if index `i` is honest, the
liar's fixed wrong value otherwise. Asking the same index again returns the
same value, always. An index out of range or a malformed body gets HTTP 400.

### `POST /submit`

```
{"N": "<decimal integer>"}
```

- `{"solved": true, "token": "FLAG{...}"}` if the integer equals `N`.
- `{"solved": false}` otherwise.

The integer must be `N` itself. Nothing else is learned from a wrong
submission.

## What you can rely on

- The promise holds: at most 70 liars, and every liar's residue is wrong.
- The 180 or more honest residues are exactly `N mod p_i`.
- The service is deterministic once started. There is no rate limit, no query
  budget, no timing signal, and nothing to exploit in the HTTP layer. The
  puzzle is arithmetic on what the service states.
- `N` is determined uniquely by what you can collect: only one integer below
  `B` agrees with all but at most 70 of the stated residues.

## Why it is not immediate

- Combining all 250 residues by the Chinese remainder theorem gives a number
  of nearly 4900 bits that has nothing visibly to do with `N`. Every lie is
  folded into it.
- A set of honest residues pins `N` down once the product of their primes
  exceeds `B`, which takes about 103 of them. But you do not know who is
  honest. If 70 lie, a random choice of 103 witnesses is liar-free with
  probability about `2^-67`.
- Asking again does not help. A liar never contradicts themselves.

Find a method that is certain, not lucky. A correct method recovers `N` in well
under a second of computation.
