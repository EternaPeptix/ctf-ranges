# VitaChain — design notes

## Brief
Build an **extremely hard** range for a vitamin shop that accepts crypto, with
every flaw **based on a real, publicly disclosed HackerOne (H1) report** (Q1–Q4).
Overengineer the difficulty; derivation over recognition.

## Sourcing
Three research passes over H1 hacktivity (crypto-payment integration; auth/ATO;
API/IDOR/SSRF/injection) produced a verified shortlist (IDs cross-checked against
HackerOne's per-report JSON where possible). See `LINEUP.md` for the mapping.

## The distinct angle (vs. the rest of the repo)
The existing EVM ranges (reentrant, delphi, gauntlet) are pure on-chain/Solidity.
VitaChain lives at the **web ↔ crypto-payment seam**: the bugs are in how the
*off-chain* backend trusts, verifies, and races against *on-chain* payments and
against itself — exactly where bounty reports cluster. A mock chain + payment
provider keeps it a stdlib-Flask range like `backlog`/`obscura`, with a sibling
`imds` service for the SSRF target.

## The six and why they're hard
| # | Report(s) | Why it's brutal black-box |
|---|-----------|----------------------------|
| c1 settle | CVE-2026-9189 / H1 #682617 | signature verifies, currency & status check out — the *missing* control (amount↔order) is invisible without the order model |
| c2 ledger | H1 #300748 | at trace level the transfer "happened"; only the top-level receipt reveals the revert |
| c3 rebate | H1 #759247 / #1717650 | a single request always behaves; only concurrent timing exposes the missing atomicity |
| c4 warehouse | H1 #1369312 / #632101 | the static filter genuinely holds — the gap is the invisible window between two DNS lookups |
| c5 passport | H1 #1210502 | the public key is unpublished; you must *recover* it from signatures before the alg-confusion even applies |
| c6 storefront | H1 #2207248 / #2166697 | opaque ids, introspection off, only one of two fields is BOLA, and the limiter has to be out-thought (count requests, not ops) |

## Difficulty levers used
- **Decoys that look like security.** c1 verifies HMAC + currency + status; c4
  blocks every static SSRF bypass; c6 disables introspection and opaques its ids;
  c5 withholds the public key. Naive front-door attempts all fail by construction.
- **Derivation, not recognition.** c5 needs real algebra (gcd modulus recovery +
  exact PKCS#1 EM reconstruction + SPKI DER); c4 needs the DNS-rebind insight; c3
  needs a real concurrent race; c2 needs the finality/receipt reasoning.
- **Faithful mocks.** The chain enforces balances for successful txs (so only a
  *reverting* tx leaks); the provider signs the attacker's chosen invoice (so the
  bug is the webhook's trust, not forgeable signatures); the DNS flip models TTL-0
  rebinding.
- **The solver does real work.** c3 wins a threaded race; c4 drives the rebind; c5
  recovers a 1024-bit modulus and rebuilds the PEM byte-identically — "green"
  proves the intended path, not a shortcut.

## Hardening against unintended solves
- c1 rejects wrong currency, non-`paid` status, and bad signatures; only the
  amount gap remains.
- c2's chain refuses a non-reverting over-balance tx, so you *must* use a revert.
- c3 keeps the balance math under a lock (no lost-update noise) — the only bug is
  the unsynchronized `used` flag; `/buy` resets the round so the self-check repeats.
- c4 blocks internal names and every static IP encoding, and refuses redirects.
- c5 only accepts a *verifying* RS256 or an HS256 forged with the real PEM; a
  tampered RS256 payload fails; recovered-N is validated by the exploit.
- c6's `invoice` field enforces ownership; only `receipt` is BOLA; the admin id is
  random per boot so it can't be hardcoded.

## Implementation
- One shared `python:3.12-slim` + Flask image (`app/`), dispatched by `$CHALLENGE`
  to `challenges/cN_*.py`; scoreboard + an internal `imds` service. Pure stdlib
  crypto/VM — no `cryptography`, no `pycryptodome`; c5's RSA (keygen, PKCS#1,
  DER/PEM) is hand-rolled.
- Secrets random per boot. `vitachain_net` is pinned to `10.84.0.0/24` because the
  host's default Docker address pools are exhausted by sibling ranges.

## Known / accepted
- Flags live in challenge source (training artifact, consistent with the repo),
  except c4's, which lives in the `imds` container and is only captured via the SSRF.
- c5 uses `e=3` (realistic, and what makes the modulus-recovery tractable); a
  1024-bit modulus keeps boot-time keygen fast. The attack is size-independent.
