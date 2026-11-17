# synapse -- solution (organizer only, spoilers)

Reference implementation: `scripts/solve.py`. Standard library only, every
number a `fractions.Fraction`, no tolerances: every test is exact equality.
Typical cost: about 1,000 `/eval` queries and one random line, a second or two
of wall time.

## Why structure is the only way in

    f(x) = sum_j a_j max(0, w_j . x + b_j) + c        n = 6, H = 10

`f` is linear on each cell of the arrangement of the 10 hyperplanes
`P_j = {x : w_j . x + b_j = 0}`. In six dimensions that is up to several
hundred cells, and no grid of samples tells you where their boundaries are. But
the whole function is determined by 10 hyperplanes plus 17 numbers, and both
can be read off exactly from queries.

Two facts carry the solution.

**Gradient jump.** Crossing `P_j` (and nothing else) from the side where unit
`j` is off to the side where it is on changes the gradient of `f` by exactly
`a_j w_j`. So the jump `U = grad_after - grad_before` across a kink is
`+-a_j w_j`: a normal vector of the hyperplane, with the output weight folded
in. Together with one point `x_k` on the hyperplane this is the hyperplane:
`{x : U . x + beta = 0}`, `beta = -U . x_k`.

**ReLU algebra.** `max(0, -u) = max(0, u) - u`, and `max(0, k u) = k max(0, u)`
for `k > 0`. So if we only know unit `j` up to the scaling `U_j = s a_j w_j`,
`beta_j = s a_j b_j` with an unknown sign `s = +-1`:

    a_j max(0, w_j . x + b_j) = sign(a_j) max(0, U_j . x + beta_j)            if s a_j > 0
                              = sign(a_j) max(0, U_j . x + beta_j) + a_j (w_j . x + b_j)   if s a_j < 0

Summing over `j`:

    f(x) = sum_j lambda_j max(0, U_j . x + beta_j) + L . x + e,     lambda_j in {+1, -1}

for some vector `L` and scalar `e`. Once the hyperplanes are known, `f` is
**linear** in the remaining unknowns `(lambda, L, e)`: 10 + 6 + 1 = 17 numbers.

## Step 1: exact local gradient

At a point `x` in the interior of a cell, for each axis `i` take a step `eps`
and test

    f(x + eps e_i) + f(x - eps e_i) - 2 f(x) == 0

Halve `eps` until it holds. The solver also requires the same at `eps/2` and
that the two central differences agree, i.e. the 5-point stencil is exactly
collinear, which rules out a convex and a concave kink cancelling in a single
second difference. On a linear stencil the central difference is the partial
derivative, exactly:

    g_i = (f(x + eps e_i) - f(x - eps e_i)) / (2 eps)

## Step 2: kinks on random lines

Take a random base point `p` (coordinates `k / 1000003`, `|p_i| <= 2`) and a
random integer direction `d` (entries in `[-9, 9]`). `F(t) = f(p + t d)` is
piecewise linear in `t`, with a kink at `t_j = -(w_j . p + b_j) / (w_j . d)`
for every unit whose hyperplane the line crosses. A random line crosses all
10; almost always all 10 crossings lie in `[-64, 64]`.

Isolate each kink exactly by recursion on an interval `[lo, hi]`:

1. If `F` at `lo + w/4`, `lo + w/2`, `lo + 3w/4` lies on the chord through
   the endpoints, the interval is linear: stop.
2. Otherwise take the slope just right of `lo` and just left of `hi` (step
   `w/16`), and intersect the two lines:

       t* = (F(hi) - F(lo) + s_L lo - s_R hi) / (s_L - s_R)

3. If `lo < t* < hi`, `F(t*)` is on the left line, and `F` agrees with the
   left line at `t* - (t* - lo)/k` and with the right line at
   `t* + (hi - t*)/k` for `k = 2, 8, 64`, the interval is a clean single bend:
   record `(t*, lo, hi)`.
4. Otherwise bisect and recurse (depth cap 48).

All evaluations are cached, and the quarter points of an interval are the
midpoints of its halves, so bisection is cheap.

The prime denominator of `p` is there so that no kink sits on a dyadic split
point: a kink exactly at a split point would make both halves linear and be
missed on that line.

## Step 3: one hyperplane per kink

For a kink `(t*, lo, hi)` let `x_k = p + t* d`. If `x_k` already lies on a
hyperplane we hold (`U . x_k + beta == 0`), skip it: this makes every line
after the first nearly free. Otherwise compute the exact gradient at the two
points halfway to each end of the interval,

    x_- = p + (t* - (t* - lo)/2) d,      x_+ = p + (t* + (hi - t*)/2) d

and set `U = g(x_+) - g(x_-)`, `beta = -U . x_k`. Canonicalize the sign (first
nonzero component of `U` positive) and dedupe by exact equality of `(U, beta)`.
Because `U` is exactly `+-a_j w_j`, the same hyperplane found on different
lines produces the identical pair.

**Confirmation.** Step 2 can in principle be fooled: two kinks of opposite
curvature that sit very close together can pass for one bend, and then `U` is
a sum of two jumps and is not a hyperplane of `f` at all. So every candidate is
confirmed independently before it is accepted. Pick two fresh random points
`y` on the candidate hyperplane (random `y`, then solve for the coordinate with
the largest `|U_i|`), a random integer direction `d'` with `U . d' != 0`, and
look at the second difference

    S(eta) = f(y + eta d') + f(y - eta d') - 2 f(y)

If `f` is bent exactly at `y`, then `S(eta) = |a_j (w_j . d')| eta` for all
small `eta`, so `S(eta) = 2 S(eta/2) = 4 S(eta/4) != 0`. If `f` is not bent at
`y`, then `S` vanishes for all small `eta`. Halve `eta` until one of the two
patterns appears. A bogus hyperplane fails this at a generic point; a real one
passes.

Shoot lines until 10 confirmed hyperplanes are held.

## Step 4: exact fit

Features of a point `x`:

    [max(0, U_j . x + beta_j) for j] + [x_1 .. x_6] + [1]          (17 columns)

Sample 51 points (three times the number of unknowns, coordinates `k/997` at
scales 1, 2, 4, 8, 16), query `f` there, and solve the linear system exactly by
Gauss-Jordan elimination over `Fraction`. The 17 feature functions are linearly
independent (each ReLU is bent on a different hyperplane), so the solution is
unique once the points see enough cells; if the rank is short, more points are
added.

The overdetermination is deliberate. If a hyperplane were still missing, `f`
would not lie in the span of the features, the system would be inconsistent,
and the solver would go back to shooting lines instead of returning a wrong
answer.

The solution always has `lambda_j in {+1, -1}`, as the algebra predicts.

## Step 5: cross-check and submit

Compare the fitted `g` with `f` on 40 further fresh points (exact equality),
then POST

    {"relus": [{"q": U_j, "r": beta_j, "p": lambda_j}], "lin": L, "const": e}

to `/verify` and read the token from the response.

## What the verifier does

`/verify` draws 400 fresh points per call: 200 in boxes `[-s, s]^6` for
`s = 1, 2, 4, 8, 16, 32` with random denominators up to 1000, and 200 placed
on each of the true kink surfaces and then nudged off by `+-1/m` (random
`m <= 10^6`), 20 per unit. The second group is what makes a near miss fail: a
submission whose hyperplane is off by a hair disagrees with `f` in a thin slab
around the surface, and that is exactly where those points are. Only the
mismatch count is returned.

## Exactness and failure modes

- No floats: requests carrying a JSON float are rejected at parse time on the
  server, and the solver refuses to parse one from a response. All step sizes,
  slopes, intersections and the linear solve are rationals.
- Every "is this linear" decision samples finitely many points, so it can be
  wrong only on a measure-zero set of alignments between the random line and
  the hidden hyperplanes. The solver is built so that such an event costs a
  line, never correctness: unconfirmed candidates are dropped, an incomplete
  hyperplane set shows up as an inconsistent fit, and the result is
  cross-checked before submission.
- Offline stress test of the same solver code against 1,000 random networks
  drawn from the service's distribution: 1,000 exact reconstructions, 927 to
  1,521 queries (mean 1,037), 1 to 4 lines.

## Shortcuts a solver might take

The parameters are small integers, so `U_j = +-a_j w_j` can be factored back
into the service's own `(a_j, w_j, b_j)` up to the sign ambiguity, which the
fit then resolves. That is not needed: `/verify` accepts any equal function.
