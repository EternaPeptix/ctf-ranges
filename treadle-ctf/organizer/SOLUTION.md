# treadle -- solution (spoilers)

The box is the textbook setting for **active automata learning with a minimally
adequate teacher**: `/run` is the membership (output) query, `/conjecture` is
the equivalence query, and the answer is **Angluin's L\***, in its Mealy form,
with **Rivest-Schapire** counterexample analysis. `scripts/solve.py` is that
and nothing else: under 300 lines with comments, standard library only, no
randomness.

## 1. Why the structure has to be learned

- The hidden machine has `n` in [24, 40] states over `k` in {2, 3} inputs and
  `g` in {2, 3} outputs, with uniformly random `delta` and `lambda`. There are
  `(n*g)^(n*k)` tables; the smallest case is `48^48 > 10^80`.
- There is no special input. `/conjecture` releases the token only for a
  machine that is equivalent on *all* strings, checked exactly.
- Output queries alone cannot certify anything (a finite sample never rules
  out a larger machine). Equivalence queries alone give one short string per
  call. The two together give a polynomial algorithm.

## 2. The idea in one paragraph

Two input prefixes `u`, `v` lead to the same state iff no suffix `e` tells them
apart, i.e. `out(u.e)` and `out(v.e)` agree on their last `|e|` symbols for
every `e` (Myhill-Nerode, Mealy version). Because the machine is minimal and
reachable, its states *are* these classes. L\* keeps a finite set `E` of
suffixes as a stand-in for "every `e`", a set `S` of prefixes that `E` proves
pairwise different, and asks the teacher for a counterexample whenever `E` is
too coarse. Every counterexample yields one more suffix and at least one more
state, so it stops after at most `n - 1` counterexamples.

## 3. The observation table

- `S`: access words, prefix-closed, initially `{""}`.
- `E`: experiments (non-empty suffixes), initially `Sigma` itself. Having every
  single symbol in `E` means a row also records the outputs of a state, which
  is what makes the Mealy hypothesis well defined.
- Cell `T(u, e)` = the last `|e|` symbols of `out(u.e)`: one `/run` call.
- `row(u)` = `(T(u, e) for e in E)`.

Rows are needed for `S` and for the one-step extensions `S.Sigma`.

**Caching.** Every cell is asked at most once. Beyond that, one `/run` on `w`
reveals `out(p)` for every prefix `p` of `w`, so the solver stores, for every
word it has seen, the output symbol emitted on that word's last input symbol,
and answers locally any query whose prefixes are all known. To make that pay,
the missing cells of a row are filled longest experiment first (`u.123` also
answers `u.1` and `u.12`). The effect is modest: about 11% fewer `/run` calls
than one request per distinct word, measured over 200 machines.

## 4. Closed and consistent

- **Closed**: for every `s` in `S` and `a` in `Sigma`, `row(s.a)` equals the row
  of some word in `S`. If not, `s.a` is a state nobody has seen: add it to `S`
  (and fill in its extensions).
- **Consistent**: if `s1`, `s2` in `S` have equal rows, then `row(s1.a)` equals
  `row(s2.a)` for every `a`. If not, some `e` in `E` has
  `T(s1.a, e) != T(s2.a, e)`; then `a.e` separates `s1` from `s2`: add it to `E`.

The solver loops `close()` / `make_consistent()` until neither changes
anything. With Rivest-Schapire handling (section 6) `S` only ever receives
words whose row is new, and adding experiments can only make rows more
different, so the rows of `S` stay pairwise distinct and the consistency step
never has anything to do. It is implemented anyway: it is the invariant the
hypothesis construction relies on, and it is what you need the moment you
handle counterexamples Angluin's original way (adding all prefixes of the
counterexample to `S`).

## 5. Hypothesis

From a closed, consistent table:

- states: the words of `S` (one per distinct row); start state: `""`
- `delta(s, a)` = the `s'` in `S` with `row(s') = row(s.a)`
- `lambda(s, a)` = `T(s, a)` (a single symbol, since `a` is in `E`)

Submit it to `/conjecture`. `solved: true` ends the run.

## 6. Counterexamples: Rivest-Schapire

The service returns a shortest `w` with `out(w) != out_H(w)`; the solver also
truncates to the first differing position, so the outputs differ exactly on
the last symbol of `w`. Let `m = |w|`. (`m >= 2` always: a one-symbol word is a
table cell of the start row, so the hypothesis cannot get it wrong.)

For `0 <= i < m` let `s_i` be the access word of the hypothesis state reached by
`w[:i]`, and

    alpha(i) = last symbol of out(s_i . w[i:])        (asked of the real machine)

- `alpha(0)` is the true last output, since `s_0 = ""`.
- `alpha(m-1)` is the hypothesis' last output: `out(s_{m-1}.a)`'s last symbol is
  the cell `T(s_{m-1}, a) = lambda_H(s_{m-1}, a)`.

They differ, so there is an `i` with `alpha(i) = alpha(0) != alpha(i+1)`. Binary
search on the predicate `alpha(i) == alpha(0)` finds one in about `log2 m` output
queries. At that `i`, write `a = w[i]` and `v = w[i+1:]`:

    out(s_i . a . v)  and  out(s_{i+1} . v)   end in different symbols,

yet the hypothesis claimed `s_i.a` and `s_{i+1}` are the same state
(`row(s_i.a) = row(s_{i+1})`). So `v` is an experiment that tells them apart.
Add `v` to `E`. Now `row(s_i.a)` differs from `row(s_{i+1})`, which was the only
row of `S` it matched, so the table is no longer closed and closing it adds at
least one state. (This also shows `v` was not already in `E`.)

Then back to section 4.

## 7. Termination and correctness

- Words in `S` have pairwise different rows, hence reach pairwise different
  states of the hidden machine. So `|S| <= n` always.
- Every counterexample strictly increases `|S|`. So at most `n - 1`
  counterexamples, at most `n <= 40` conjectures.
- When `|S| = n` and the table is closed, `S` holds exactly one access word per
  hidden state, `delta` and `lambda` of the hypothesis are forced to be the
  true ones, and the hypothesis is isomorphic to the hidden machine. The
  teacher confirms it and hands over the token.

## 8. Cost

Worst case: at most `(1 + k*n) * (k + n - 1)` table cells plus `n * log2(2n)`
binary-search queries; for `n = 40`, `k = 3` that is about 5,300 `/run` calls and
40 `/conjecture` calls. Random machines are much kinder: a new experiment
usually splits many states at once, so `E` stays small.

Measured over 1000 freshly generated machines (the service's own generator,
solver driven through the real Flask routes in-process):

| | min | median | max |
|---|---|---|---|
| `/run` calls actually sent | 124 | 373 | 916 |
| `/conjecture` calls | 2 | 6 | 11 |
| longest `/run` input (symbols) | | | 20 |

1000 / 1000 recovered. Three treadles cost about twice as many `/run` calls as
two (median 510 against 266). A `make check` run takes about a second.

## 9. The service side, for the record

`app/serve.py`:

- **Generation.** Pick `|Sigma|`, `|Gamma|` in {2, 3} and a raw size in
  [24, 52]; fill `delta` and `lambda` uniformly at random; pick a random start.
  Drop unreachable states (BFS), then minimise by partition refinement (start
  from "same output row", split by successor blocks until stable) and take the
  quotient. Keep the machine only if the resulting count is in [24, 40] and
  every symbol of `Gamma` is actually emitted; otherwise draw again. About two
  attempts in three are kept, and the count comes out close to uniform on
  [24, 40]. The kept machine is re-checked for reachability and minimality
  before the service starts.
- **`/run`.** Walks the machine from the start state.
- **`/conjecture`.** Validates the submitted machine (complete over `Sigma`,
  outputs in `Gamma`, at most 2048 states), then runs a BFS over the product of
  hidden machine and draft from the pair of start states. Pairs are expanded in
  FIFO order with symbols in `Sigma` order, so the first output mismatch closes
  a shortest (and, among shortest, lexicographically first) distinguishing
  word. No mismatch in the whole reachable product means equivalence.
- **Secrets.** Machine from `random.SystemRandom`, token
  `FLAG{<32 hex>}` from `secrets`, both in memory only, both new on every
  start.

## 10. Other routes to the same token

Any correct active-learning algorithm works against this teacher: Angluin's
original counterexample handling (add all prefixes of `w` to `S`, then the
consistency step earns its keep), Maler-Pnueli (add all suffixes to `E`),
discrimination-tree learners (Kearns-Vazirani, Observation Pack, TTT), or
L\#. They differ only in query counts. A solver that ignores `/conjecture`'s
counterexamples and tries to certify a hypothesis by output queries alone
(W-method style) also works here in principle, because the state bound of 40
is public, but needs far more `/run` calls.
