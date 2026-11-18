# Solution (organizer -- spoilers)

The block hides a connected, sparse, weighted graph on `n = 30` studs. The
only measurement is the effective resistance between two studs. The wiring
comes out of **all** the readings at once, by one exact matrix inversion.

## 1. Resistance is a squared distance

Write the wiring as its Laplacian `L = D - W`:

```
L_ij = -w_ij   (i != j, 0 if there is no wire)        L_ii = sum_j w_ij
```

`L` is symmetric, positive semidefinite, and because the graph is connected
its null space is exactly the constant vector `1`.

Feed one unit of current in at `a` and draw it out at `b`. Kirchhoff's current
law at every stud is `L v = e_a - e_b` for the vector of potentials `v`, so
`v = L+ (e_a - e_b)` with `L+` the Moore-Penrose pseudoinverse, and

```
R_ab = v_a - v_b = (e_a - e_b)^T L+ (e_a - e_b) = L+_aa + L+_bb - 2 L+_ab
```

`L+` is positive semidefinite of rank `n - 1`, so it is the Gram matrix of `n`
points `x_0 .. x_{n-1}` in `R^(n-1)` (with centroid 0), and the line above
says `R_ab = |x_a - x_b|^2`. **The table of readings is a Euclidean
squared-distance matrix.** Turning distances back into a Gram matrix is a
solved problem (classical multidimensional scaling), and the Gram matrix here
is `L+`, which is one inversion away from `L`.

## 2. Fiedler's bordered inverse

Let `R` be the `n x n` matrix of readings (zero diagonal). Then

```
[ R    1 ] -1      [ -L/2   y ]
[ 1^T  0 ]     =   [  y^T   z ]
```

so the wiring is `-2` times the top-left block of the inverse of the
`(n+1) x (n+1)` bordered matrix.

Proof. With `d = diag(L+)`, section 1 reads `R = d 1^T + 1 d^T - 2 L+`. Use
`L 1 = 0` and `L+ L = I - J/n` (`J` = all ones):

```
R L = 1 d^T L - 2 (I - J/n)
R (-L/2) + 1 y^T = I          with  y = L d / 2 + 1/n
1^T (-L/2) = 0
```

Those are exactly the equations that say the first `n` columns of the inverse
are `[-L/2 ; y^T]`. The bordered matrix is invertible: if `R c + s 1 = 0` and
`1^T c = 0`, then `0 = c^T R c = -2 c^T L+ c`, so `c` is a multiple of `1`,
hence `c = 0` and `s = 0`.

Equivalent route (double centering): with `P = I - J/n`,
`L+ = -1/2 P R P`, and then `L = (L+ + J/n)^-1 - J/n`. Same cost, one
inversion. Both routes were checked against each other on 150 draws.

## 3. The reference solver (`scripts/solve.py`)

1. `GET /` for `n`.
2. `POST /resistance` for every pair `i < j`: `C(30,2) = 435` readings, parsed
   into `fractions.Fraction`.
3. Build the `31 x 31` bordered matrix and invert it by Gauss-Jordan over
   `Fraction`. The diagonal of `R` is zero, so the elimination needs a pivot
   search with row swaps.
4. `L = -2 *` (top-left block). For `i < j`: `weight(i, j) = -L_ij`. Because
   the arithmetic is exact, **every unwired pair comes out as an exact 0**;
   there is no threshold to choose. The solver also checks that the result is
   a Laplacian (symmetric, rows sum to 0, no negative weight, connected).
5. `POST /submit` the wires, print `TOKEN: FLAG{...}`.

It is deterministic and uses only the three public endpoints. A full run is
about a second: ~0.2 s for the readings, ~0.1 s for the elimination (the
readings have denominators of a few dozen digits; 31 was the widest seen in
150 test draws).

## 4. Why nothing local works

- Every pair has a finite reading, wired or not.
- Across a wire, `R_ij <= 1/w_ij`, with equality only for a bridge. Any loop
  through the wire lowers the reading, by an amount that depends on the whole
  network. (Foster: `sum over wires of w_ij R_ij = n - 1`.)
- "Low reading means wire" is false. Weights span `1/6 .. 9`, so a weak wire
  reads high and two studs joined through a strong path read low. The server
  redraws any instance in which a single cut-off would separate wired from
  unwired pairs, and in 150 test draws "the m lowest readings are the m wires"
  failed 150 times. The solver prints the two numbers for the live instance,
  e.g. lowest unwired reading 0.36 against highest wired reading 5.00.
- A stud of degree 1 can be spotted (its row is its neighbour's row plus a
  constant) and peeled off, but that only strips the tree-like fringe. The
  instance has 11 to 16 independent loops, and the loopy core does not peel.

## 5. Other ways through

- **Floats, then rounding.** Inverting the same bordered matrix in double
  precision leaves noise of about `1e-13` on unwired pairs, and the true
  weights have denominators of at most 6, so thresholding at `1e-6` and
  `Fraction(x).limit_denominator(...)` also recovers the exact wiring (150 of
  150 test draws). It is the same idea with a rounding step; it is accepted,
  and it is fine that it is.
- **Kirchhoff as a linear system.** All potential differences for any
  injection pair are known from the readings (`v_i - v_j` for current `a -> b`
  is `(R_ib - R_ia - R_jb + R_ja) / 2`), and Kirchhoff's current law at each
  stud is linear in the unknown weights. Enough injection pairs pin them down.
  This is the inversion above written out by hand.
- **Guessing** does not work: `/submit` answers one bit, and the search space
  is the choice of ~42 wires out of 435 pairs times their weights.

## 6. What the service draws (`app/serve.py`)

Once, at startup, from the OS random source:

- a random spanning tree on the 30 studs (shuffle the studs, hang each on a
  random earlier one), so the graph is connected;
- 11 to 16 extra wires on distinct unwired pairs, so 40 to 45 wires in all out
  of 435 pairs;
- a weight `p/q` per wire, `p` in `1..9`, `q` in `1..6`;
- the token `FLAG{<32 hex>}` and a public `instance` id.

It then computes `L+ = (L + J/n)^-1 - J/n` exactly over `Fraction`, checks the
identities `L L+ = I - J/n`, `L+ = L+^T`, `L+ 1 = 0` exactly (it refuses to
start otherwise), and tabulates `R_ij = L+_ii + L+_jj - 2 L+_ij`. Nothing
drawn is printed or logged, and per-request logging is off.

`/submit` adds up the submitted weights per unordered pair, builds the
Laplacian of that, and compares it entry by entry with the hidden one (full
scan, no early exit). So any description of the same weighted graph is
accepted: any order, either orientation, unreduced fractions, integers,
a wire split into parallel parts, explicit zero weights on unwired pairs. A
wrong submission returns only `{"solved": false}`. Malformed input (bad
labels, `i = j`, a weight that is not an exact fraction or integer, more than
1740 entries, more than 512 kB) gets a 400/413 with a format message.

## 7. Check

```
make up && make check          # PASS, exit 0
make check                     # same instance, same token
make reset && make check       # fresh wiring and token, PASS again
```
