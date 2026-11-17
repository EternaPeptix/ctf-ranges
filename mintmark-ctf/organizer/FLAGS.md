# Flags (organizer)

One flag, **earned** (not hardcoded): the service mints a fresh
`FLAG{mintmark_two_seals_one_die_<random>}` at startup and reveals it from
`POST /open` only to the exact secret message `m` recovered by opening the vault.
Verified live via `scripts/solve.py` — `make check` opens the vault by GCD across
the directory and recovers the token (exit 0), repeatably.

| Widget | Port | Technique required | Flag |
|--------|------|--------------------|------|
| mintmark | 9100 | **cross-directory GCD** (pairwise / batch GCD) to find one shared prime, factor the vault, invert `e`, and decrypt `c` | `FLAG{mintmark_two_seals_one_die_<random per boot>}` |

## The technique (why it's the whole point)
A directory of `N=128` entries, each a 1024-bit product of two 512-bit primes.
Exactly one prime is reused — shared between the **vault** `V = V_v` and one other
entry. The vault on its own is unfactorable: no small factors, and `|p−q|` is kept
large so Fermat's method fails. It yields *only* to the directory:
```
for i != v:  g = gcd(V, V_i)      # the partner gives 1 < g < V = the shared prime p
q = V // p;  d = e^-1 mod (p-1)(q-1);  m = c^d mod V   # then POST /open {m}
```
The reference solver also runs a true **batch GCD** (product/remainder tree) over
the whole register as an independent check that exactly one pair shares a factor.

## The emergent lesson (and its real one-off)
This re-creates **"Mining your Ps and Qs" (Heninger, Durumeric, Wustrow, Halderman,
USENIX Security 2012)** and the concurrent **"Ron was wrong, Whit is right"
(Lenstra et al.)**: an internet-wide scan found that a sliver of RSA moduli shared
a prime — not because any key was weak, but because low-entropy embedded devices
occasionally drew the *same* prime at boot. A single key is secure; the
**population** is not. The vulnerability is invisible when auditing one key and
only appears across the set — a genuinely *emergent* security property, found by
sheer circumstance (a measurement study), and near-absent from bug-bounty corpora.

## Reference solver stats
- Opens the vault in ~1 ms (pairwise scan) / tens of ms (batch GCD over all 128);
  a full `make check` run is a fraction of a second after boot.
- Pure stdlib, no randomness — a run is a deterministic function of the box. The
  register + token are OS-random per boot, so `make reset && make check` stays green.

## Notes
- No scoreboard: single-service range; the flag is the `/open` token.
- `mintmark_net` is pinned to an explicit `10.87.0.0/24` (host default pools exhausted).
- The service runs a full self-audit before listening (all 8128 pairs coprime except
  one; it solves its own puzzle from public values), so a boot that serves traffic is
  guaranteed solvable.
- Built by Fable 5.2 (mint-strongroom "two seals, one die" theme, its creative choice)
  to spec; serve.py and the solver were reviewed and the self-check re-run here (token
  format aligned to `FLAG{...}` for the collection).
