# orrery -- brief

## The setting

On the table stands a brass orrery with six arms. Behind its dial plate, where
nobody is allowed to look, sits a gear train: a handful of wheels, each meshing
with some of the arms, each carrying its own weight. Set the six arms to any
positions you like and the pointer on the front swings to a single number.

The mainspring is short. Each time the orrery is wound it will give exactly
**32 readings** and then no more. Tell it its own gear train, wheel for wheel,
and it hands you a token.

Without the brass: the service holds a hidden **sparse polynomial**

```
f(x0, x1, x2, x3, x4, x5)  =  sum over j of  c_j * x0^e_j0 * x1^e_j1 * ... * x5^e_j5     (mod p)
```

over the finite field `F_p`, where `p` is a fixed, public prime of 301 bits.

- **6 variables** (the arms).
- **At most 16 terms** (the wheels). How many there actually are is secret.
- Every exponent `e_jk` is an integer in **0..20**. The exponents are secret.
- Every coefficient `c_j` is a nonzero residue mod `p`. The coefficients are secret.
- No two terms share an exponent vector.

`f` is drawn at random when the service starts and stays fixed for as long as
it is up. A restart draws a new `f`, a new token and a full budget.

## The goal

**Recover `f` exactly** -- every term, every exponent, every coefficient -- and
submit it. If what you submit equals `f` as a polynomial, the service returns a
completion token of the form `FLAG{...}`.

## The service

Base URL: `http://app/` on the puzzle network (`http://localhost:9500/` from the host).
All requests and responses are JSON.

### `GET /`

Describes the box: the prime `p`, the bounds above, the evaluation budget (with
how much of it is left) and the endpoints. Free. It never reveals the terms.

### `POST /eval`

Set the arms, read the pointer.

```
request   {"x": [v0, v1, v2, v3, v4, v5]}
response  {"y": 1234567890123456789}
```

`x` is a list of exactly six integers; they are taken modulo `p`. `y` is
`f(x) mod p`, an integer in `0..p-1`. (The value above only illustrates the
format; real answers have about 90 digits.)

**Every answered call costs one of the 32 evaluations**, including a repeat of
a point you have already asked. The response header `X-Evaluations-Remaining`
and `GET /` both say how many are left. Once they are gone the endpoint answers
HTTP 429 until the service is restarted.

### `POST /submit`

Name the gear train.

```
request   {"terms": [[e0, e1, e2, e3, e4, e5, coeff], ...]}
response  {"solved": true, "token": "FLAG{...}"}
     or   {"solved": false}
```

Each term is a list of seven integers: six exponents, then the coefficient
(taken modulo `p`). The order of the terms does not matter. The check is
equality of polynomials: like terms are added together and terms with a zero
coefficient are ignored before comparing. Submitting is free and does not touch
the evaluation budget, but a wrong submission tells you nothing beyond "no".

Malformed requests to either endpoint get HTTP 400 and an `error` string, and
cost nothing.

## Rules

- Query access only. The puzzle is the polynomial, not the container: do not
  inspect the service's process, image, memory or logs, and do not restart it.
- The budget is hard. It is shared by everyone talking to the box, it does not
  refill, and there is no way to buy more. Decide what you are going to ask
  before you ask it, and keep every answer you pay for.
- The numbers are big. `p`, the answers and the coefficients are plain JSON
  integers of about 90 decimal digits; use a parser with arbitrary-precision
  integers (Python's `json` is fine, anything that goes through 64-bit floats
  is not).
- The obvious approaches are out of reach by a wide margin:
  - There are `21^6 = 85,766,121` possible monomials, so treating `f` as a
    dense polynomial means that many unknowns against 32 equations.
  - Peeling the variables apart one at a time takes hundreds of evaluations.
  - Over the integers one could plug in a huge base and read the terms off the
    digits of the answer. Here every answer is reduced mod `p` and the
    coefficients are themselves random residues, so there are no digits to read.
  - Guessing is hopeless: one term alone has `21^6 * (p - 1)` possibilities.
- The puzzle is fair: 32 evaluations are enough to recover any `f` within the
  stated bounds, with certainty, in well under a second of computation.
