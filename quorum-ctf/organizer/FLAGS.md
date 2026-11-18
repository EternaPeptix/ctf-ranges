# Flags (organizer)

One flag, **earned** (not hardcoded): a fresh `FLAG{quorum_<hex>}` is minted at
startup and returned by `POST /submit` only to the exact hidden integer `N`.
Verified live via `scripts/solve.py` — `make check` recovers `N` despite the
liars and gets the token (exit 0), repeatably across resets.

| Widget | Port | Technique required | Flag |
|--------|------|--------------------|------|
| quorum | 9400 | Chinese Remainder with errors = integer **Berlekamp–Welch** / rational reconstruction | `FLAG{quorum_<random per boot>}` |

## The technique (why it's the whole point)
250 witnesses each hold a distinct 20-bit prime and state `N mod p_i`; up to 70
lie (a fixed wrong residue, consistent). Plain CRT over all 250 folds the lies in
and yields garbage; guessing ~100 honest primes is astronomically unlikely.

The decode: CRT all residues to `R mod Mprod` (`Mprod = Π p_i`). Let `E` be the
(unknown) product of the liars' primes. Then `E·R ≡ E·N (mod Mprod)` with both `E`
and `E·N` small, so the pair `(E·N, E)` is recoverable by **rational
reconstruction** (extended Euclid on `(Mprod, R)` stopped at the right bound), and
`N = (E·N)/E`. Guaranteed whenever `2·B·E_max² < Mprod` (`E_max` = product of the
70 largest primes) — the service checks this on its actual draw at boot and
refuses to serve otherwise.

This is the integer analogue of **Reed–Solomon / Berlekamp–Welch** error-correcting
decoding: the errors (lies) are located and removed by multiplying the unknown by
the unknown product of the faulty moduli, and Euclid hands back both.

## Reference solver stats
- Collects all 250 residues, CRTs, does one extended-Euclid rational reconstruction,
  and asserts `≤70` residues disagree and `b` equals the product of exactly those
  primes before submitting. Pure stdlib, exact, deterministic; a `make check` run is
  a fraction of a second.
- `N`, the liar set, their wrong residues, and the token are OS-random per boot, so
  `make reset && make check` stays green.

## Notes
- No scoreboard: single-service range; the flag is the `/submit` token.
- `quorum_net` is pinned to an explicit `10.91.0.0/24` (host default pools exhausted).
- The service keeps secrets out of its logs and self-audits at boot (each answer is
  wrong iff that witness is a liar; the recovery inequality holds).
- Built by Fable 5.2 (a "bench of witnesses, at most 70 liars" theme, its creative
  choice) to spec; serve.py and the solver were reviewed and the self-check re-run
  here (token aligned to `FLAG{...}` for the collection).
