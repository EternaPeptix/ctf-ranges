# counterpoise -- solution (spoilers)

## The idea in one paragraph

A reading is an integer, not a yes/no, so one weighing can carry far more than
one bit. The trick is to choose all 255 weighings in advance so that the 255
integers together pin down every one of the 1024 tins. A **detecting matrix**
does exactly that: a 255 x 1024 matrix `D` with entries in `{-1, 0, +1}` such
that `D.x` is different for every 0/1 vector `x`. Each row is one weighing
(`plus` = its `+1` columns, `minus` = its `-1` columns). The recursive
Cantor-Mills construction gives such a matrix with `2^k - 1` rows and
`k * 2^(k-1)` columns; `k = 8` is exactly 255 x 1024. The same recursion that
builds the matrix also decodes it, exactly, with nothing but parity and
halving. No question depends on an earlier answer, there is no randomness and
no search.

## The matrix

```
D_1 = [ 1 ]

            [  D    D    I    0 ]        D = D_k
D_{k+1}  =  [  D   -D    0    0 ]        I = identity of size (rows of D_k)
            [  0    0    0    1 ]        last column and last row: a single 1
```

If `D_k` has `r` rows and `c` columns, `D_{k+1}` has `2r + 1` rows and
`2c + r + 1` columns. Starting from 1 x 1:

| k | rows `2^k - 1` | columns `k * 2^(k-1)` |
|--:|---------------:|----------------------:|
| 1 |              1 |                     1 |
| 2 |              3 |                     4 |
| 3 |              7 |                    12 |
| 4 |             15 |                    32 |
| 5 |             31 |                    80 |
| 6 |             63 |                   192 |
| 7 |            127 |                   448 |
| 8 |        **255** |              **1024** |

That table is the ladder printed in `challenge/BRIEF.md`. The two smallest
non-trivial cases written out:

```
D_2 =  1  1  1  0        D_3 =  1  1  1  0   1  1  1  0   1  0  0   0
       1 -1  0  0               1 -1  0  0   1 -1  0  0   0  1  0   0
       0  0  0  1               0  0  0  1   0  0  0  1   0  0  1   0
                                1  1  1  0  -1 -1 -1  0   0  0  0   0
                                1 -1  0  0  -1  1  0  0   0  0  0   0
                                0  0  0  1   0  0  0 -1   0  0  0   0
                                0  0  0  0   0  0  0  0   0  0  0   1
```

Every entry is `-1`, `0` or `+1`, so every row is a legal question: no tin is
on both pans and none appears twice.

## Why it determines the wall (and how to decode)

Split the unknown 0/1 vector to match the column blocks: `v = (x, y, z, w)`
with `x` and `y` of length `c`, `z` of length `r`, `w` a single bit. The
readings `m = D_{k+1}.v` split into three blocks:

```
a = D.x + D.y + z        (top r readings)
b = D.x - D.y            (middle r readings)
w                        (last reading)
```

1. `w` is read directly.
2. `a - b = 2*(D.y) + z`. The first term is even and `z` is 0/1, so
   **`z = (a - b) mod 2`**, entry by entry. Equivalently: `D(x+y)` and
   `D(x-y)` have the same parity, so the parity mismatch between `a` and `b`
   is `z`.
3. With `z` known, `D.x = (a - z + b) / 2` and `D.y = (a - z - b) / 2`. Both
   divisions are exact.
4. `D.x` and `D.y` are two sets of readings of the smaller matrix `D_k` on two
   0/1 vectors. Recurse. At `k = 1` the single reading *is* the bit.

Every step is forced, so by induction `D_k.v` determines `v`: the matrix is
detecting. Decoding costs a handful of integer operations per entry.

Worked example on rung 2, tins `(t0, t1, t2, t3) = (1, 0, 1, 1)`:

```
a = t0 + t1 + t2 = 2      b = t0 - t1 = 1      w = t3 = 1
z  = (a - b) mod 2 = 1            -> t2 = 1
Dx = (a - z + b) / 2 = 1          -> t0 = 1
Dy = (a - z - b) / 2 = 0          -> t1 = 0
```

## The reference solver (`scripts/solve.py`)

Standard library only. The method is two functions, about 20 lines:

```python
def detecting(k):
    D = [[1]]
    for _ in range(k - 1):
        r, c = len(D), len(D[0])
        top = [row + row + [int(i == j) for j in range(r)] + [0] for i, row in enumerate(D)]
        mid = [row + [-v for v in row] + [0] * (r + 1) for row in D]
        D = top + mid + [[0] * (2 * c + r) + [1]]
    return D

def decode(m, k):
    if k == 1:
        return [m[0]]
    r = 2 ** (k - 1) - 1
    a, b = m[:r], m[r:2 * r]
    z = [(p - q) % 2 for p, q in zip(a, b)]
    dx = [(p - e + q) // 2 for p, q, e in zip(a, b, z)]
    dy = [(p - e - q) // 2 for p, q, e in zip(a, b, z)]
    return decode(dx, k - 1) + decode(dy, k - 1) + z + [m[2 * r]]
```

What a run does:

1. `GET /` until the box answers (it may still be booting after `make up`),
   and read `n`, `budget`, `asked`. If fewer than 255 questions are left on the
   current wall it stops with a clear message instead of wasting them.
2. Build `D_8` and send its 255 rows as 255 `POST /weigh` calls, in order,
   without looking at any answer. Column `j` of the matrix is tin `j`: at the
   top level `x` is tins 0..447, `y` is 448..895, `z` is 896..1022, `w` is
   tin 1023. Rows touch between 1 and 255 tins, 128 on average.
3. `decode` the 255 readings into 1024 bits, then check locally that the
   decoded bits reproduce all 255 readings (free: no extra questions).
4. `POST /submit` and print `TOKEN: FLAG{...}`.

Total: exactly 255 questions, zero to spare. A network error on a question is
retried only after `GET /` confirms the box did not charge it.

Expected `make check` output (ones-count and token vary per wall / per boot):

```
[*] http://app: n=1024, budget=255, already asked=0
[*] design fixed up front: 255 questions over 1024 positions
[*] asked 255 questions, all of them before looking at any answer
[*] decoded 1024 bits (497 ones); they reproduce all 255 readings
TOKEN: FLAG{82a492f21367116436ed6eea781e8e50}
[verify] PASS: hidden vector recovered within the question budget, token released
```

## What the service does (`app/serve.py`)

- **Startup.** Draws the wall uniformly from `{0,1}^1024` with
  `secrets.randbits(1024)` and the token as `FLAG{<32 hex>}` with
  `secrets.token_hex(16)`. Neither is logged or served; `GET /` returns only
  the card and the counters.
- **`POST /weigh`.** Under one lock: refuse with `429` if 255 questions have
  been answered; otherwise validate, and only then charge and answer.
  Validation rejects (with `400`, uncharged): a body that is not an object, a
  missing `plus` or `minus`, a non-list, any entry that is not a plain integer
  in `0..1023` (booleans, floats, strings and negative numbers are all
  refused), and any index that appears twice anywhere across the two lists. So
  the only coefficients a player can ever apply to a tin are `-1`, `0`, `+1`.
  Because the check, the charge and the answer happen under the same lock,
  parallel requests cannot squeeze out a 256th answer.
- **`POST /submit`.** Requires exactly 1024 characters of `0`/`1`
  (constant-time comparison). Wrong: `{"solved":false}`, nothing else changes.
  Right: `{"solved":true,"token":...}`.
- **After a correct submission** the wall is retired: a new hidden vector is
  drawn and the counter returns to 0 (the token stays the one set at startup).
  This is the one thing the box does beyond the bare rules, and it exists so
  that a solved box is usable again and `make check` can be run repeatedly
  without `make reset`. It never gives a player more than 255 questions about
  any single wall, and it only happens to someone who already holds the token.
  An unsolved wall whose budget is spent stays dead until the box restarts.

## How tight is 255?

- **Counting.** A reading takes at most 1025 values, so 1024 unknown bits need
  at least `1024 / log2(1025)`, i.e. 103 questions.
- **Entropy.** With all questions fixed in advance and a uniformly random wall,
  a reading is a shifted binomial and carries at most `H(Bin(1024, 1/2))`,
  about 6.05 bits. So a non-adaptive design needs at least `1024 / 6.05`,
  i.e. 170 questions.
- **Asymptotics.** The classical asymptotic answer for coin-weighing problems
  of this kind is about `2n / log2(n)` weighings for `n` coins, and this
  recursion approaches that rate as `k` grows. Lower-order terms still matter
  at this size; for `n = 1024` the formula gives about 205.

So 255 is not claimed to be the minimum. It is within a small factor of the
bounds above, it is what this clean recursion gives at exactly `n = 1024`, and
it is a quarter of the naive 1024.

## Other ways through

The box only checks the result. Any method that recovers the wall within 255
readings is a solve; the service does not require the questions to be fixed in
advance or to be these particular 255. The reference design is simply the
cleanest route: fixed questions, exact decoding, no search, and no dependence
on what the wall happens to hold.

Submissions are free and unlimited, but each one yields a single yes/no, so
they cannot stand in for weighings.

## Background reading

- H. S. Shapiro and S. Söderberg, "A combinatory detection problem" (1963).
- P. Erdős and A. Rényi, "On two problems of information theory" (1963).
- B. Lindström, "On a combinatory detection problem" (1964).
- D. G. Cantor and W. H. Mills, "Determination of a subset from certain
  combinatorial properties" (1966): `2^k - 1` weighings for `k * 2^(k-1)` coins.

The classical statements are about a spring scale (questions with 0/1
coefficients). This box allows signed questions, which is the easier setting
and the one the recursion above is written for.
