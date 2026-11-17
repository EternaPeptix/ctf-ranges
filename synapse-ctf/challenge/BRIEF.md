# synapse -- brief

## The setting

A service holds a hidden function

    f : Q^6 -> Q

`f` is **piecewise linear**. Concretely it is a one-hidden-layer ReLU network

    f(x) = sum_{j=1..10} a_j * max(0, w_j . x + b_j) + c

whose parameters are secret integers of small magnitude: `w_j` in `Z^6`,
`b_j`, `a_j`, `c` in `Z`. Every `a_j` is nonzero, every `w_j` is nonzero, and
no two `w_j` are parallel. The parameters are fixed for as long as the service
is up and are different each time it is started.

You may evaluate `f` at any rational point you like. That is the only access
you get.

## The goal

**Reconstruct `f` exactly, as a function**, and submit your reconstruction.
If it is equal to `f`, the service returns a completion token of the form
`FLAG{...}`.

You do not have to recover the service's own parameters. Any expression of the
form below that defines the same function is accepted:

    g(x) = sum_k p_k * max(0, q_k . x + r_k) + lin . x + const

with rational `q_k` in `Q^6`, `r_k`, `p_k`, `lin` in `Q^6`, `const`, and at most
64 ReLU terms.

## The service

Base URL: `http://app/` on the puzzle network (`http://localhost:8800/` from the host).

All numbers are exact rationals. Send a number as a JSON integer or as a
string `"p/q"` (or `"p"`), at most 1024 characters. JSON floats are rejected.
Results come back as strings `"num/den"` in lowest terms.

### `GET /`

Returns a JSON description of the puzzle: `n`, `H`, the input domain and the
endpoints.

### `POST /eval`

```
request   {"x": ["1/2", "-3", 0, "7/5", "22/7", "1"]}
response  {"y": "-41/10"}
```

`y` is exactly `f(x)`. `x` must have 6 coordinates. (The values above only
illustrate the format.)

### `POST /verify`

```
request   {"relus": [{"q": ["p/q", ... 6 of them], "r": "p/q", "p": "p/q"}, ...],
           "lin":   ["p/q", ... 6 of them],
           "const": "p/q"}
response  {"solved": true,  "token": "FLAG{...}"}
     or   {"solved": false, "mismatches": 137}
```

The service evaluates your `g` and compares it with `f` on 400 fresh random
rational points, drawn anew for every call. The comparison is exact equality
of rationals. Every point must match.

## Rules

- Query access only. The puzzle is the mathematics, not the container: do not
  inspect the service's process, image, or memory.
- There is no rate limit and no query budget, but dense sampling will not get
  you anywhere in six dimensions. A good solution needs on the order of a
  thousand evaluations.
- Approximations do not pass. Work in exact arithmetic.
