# fathom -- brief

A sounding line hangs over a trench. The gauge at the top reads a single real
number, **alpha**. You can pay out as much line as you like and read alpha to
as many decimal places as you want. That is all the gauge will ever tell you.

Alpha is not an arbitrary number. It is the largest real root of a hidden
polynomial

```
P(x) = c0 + c1*x + c2*x^2 + c3*x^3 + c4*x^4 + c5*x^5 + c6*x^6
```

**Name P and the service hands you the token.**

## What is known about P

- Degree exactly **6**.
- Every coefficient is an integer with **|ci| <= 100000**.
- P is **irreducible** over the rationals (it does not factor into
  lower-degree polynomials with rational coefficients).
- P is in canonical form: **primitive** (gcd of c0..c6 is 1) and **c6 > 0**.
- P has at least one real root; alpha is the largest one.
- P and the token are drawn fresh every time the service starts.

## The service

Base URL: `http://app` on the puzzle network, `http://localhost:9700` from the
host. All bodies are JSON.

| Call | Body | Reply |
|---|---|---|
| `GET /` | -- | the facts above and the endpoint list |
| `POST /digits` | `{"n": k}`, `0 <= k <= 1000` | `{"n": k, "digits": floor(alpha * 10^k), "digits_str": "..."}` |
| `POST /submit` | `{"coeffs": [c0, c1, c2, c3, c4, c5, c6]}` | `{"solved": true, "token": "FLAG{...}"}` or `{"solved": false}` |

Details that matter:

- `digits` is an **exact integer**: alpha truncated (floored) to `k` places
  after the decimal point, never rounded and never a float. Ask for 30 places
  and all 30 are right. `digits_str` is the same integer as a string, for
  tools whose JSON parser cannot hold big integers.
- `floor` rounds toward minus infinity, so the integer is negative when alpha
  is negative.
- `/submit` wants the constant term first and the canonical form above.
  `-P`, or a multiple of P, is answered with `{"solved": false}`.
- There is no limit on the number of requests and no penalty for a wrong
  submission.

```
$ curl -s -X POST localhost:9700/digits -H 'Content-Type: application/json' -d '{"n": 12}'
{"n":12,"digits":1395092667537,"digits_str":"1395092667537"}
```

means `alpha = 1.395092667537...` for that particular start of the service.

## What will not work

- **Guessing.** There are `(2*100000 + 1)^7`, about `1.28 * 10^37`,
  coefficient vectors. `/submit` only ever says yes or no.
- **Numeric fitting.** Any amount of floating-point root-finding or
  least-squares fitting yields real numbers near *some* polynomial; it does
  not yield the seven exact integers, and a 64-bit float cannot even hold the
  readings.

The digits of alpha do determine P completely. The puzzle is to get from one
to the other.

## Rules

- The HTTP API above is the whole interface. The service's container, image
  and logs are out of scope.
- Any language. The reference solution uses only the Python standard library
  and runs in well under a second.
- Solved means: a `POST /submit` answered with `"solved": true` and a
  `FLAG{...}` token.
