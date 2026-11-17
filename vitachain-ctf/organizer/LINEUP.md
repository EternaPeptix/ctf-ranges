# VitaChain — locked challenge lineup (from H1 research)

Six extremely-hard challenges, each a faithful minimal re-impl of a real,
disclosed HackerOne report / CVE, spanning distinct skills. ≥2 are the
crypto-payment theme centerpiece. Ports 8701–8706, scoreboard 8700.

| # | Name | Category | Based on (real, disclosed) | Core flaw |
|---|------|----------|----------------------------|-----------|
| c1 | **settle** | Crypto payment | CVE-2026-9189 (CF7 PayPal/Stripe add-on); H1 #682617 Starbucks | webhook signature is **valid**, but the handler never binds **amount/currency ↔ order** — a real $1 payment tagged with the target invoice marks a $5000 order paid |
| c2 | **ledger** | Crypto (on-chain) | H1 #300748 Coinbase (ETH balance manipulation) | deposit indexer credits **internal value-transfer traces** without checking the **top-level receipt status** — a pay-then-revert tx credits you, funds never move |
| c3 | **rebate** | Business logic / race | H1 #759247 Reverb (gift-card redeem race); #1717650 Stripe | redeem = check-then-credit, **non-atomic** → K concurrent requests all pass the "not redeemed" check → double-spend store credit |
| c4 | **warehouse** | SSRF / infra | H1 #1369312 Concrete CMS + #632101 GitLab | URL allowlist resolves DNS **once to validate**, the client resolves **again to fetch** — a TOCTOU **rebind** record flips public → `imds` to steal cloud creds |
| c5 | **passport** | Auth / crypto | H1 #1210502 Jitsi/8x8 (JWT key confusion) + RSA-pubkey-from-signatures | public key isn't published; recover modulus `N` via `gcd(sᵢ^e − EMᵢ)` from two RSA-signed JWTs, then forge an **HS256** admin token with the recovered PEM as the HMAC key |
| c6 | **storefront** | API / IDOR | H1 #2207248 Shopify (GraphQL BOLA) + #2166697 HackerOne (alias batching) | introspection off; opaque `gid://` node IDs with a **per-operation** authz gap, and a rate limiter that counts HTTP requests → **alias-batch** past it to read an admin-only field |

## Difficulty / overengineering plan (per challenge)
- **c1** decoys: webhook *does* verify HMAC and *does* check `currency` and
  `payment_status=="paid"` (the CVE-2026-41432 completed≠paid subtlety) — only the
  amount↔order binding is missing, so naive tampering fails.
- **c2** the "chain" is mocked in-app: a `/broadcast` builds a tx with internal
  transfers + a final reverting call; `/scan` indexes traces and ignores
  `receipt.status`. Attacker must construct the pay-then-revert tx.
- **c3** `solve.py` must win a *real* race (threaded concurrent POSTs); a naive
  per-session guard is present but defeatable; serial requests never trip it.
- **c4** faithful rebind via an in-app flip resolver + a sibling `imds` service;
  the allowlist blocks every static bypass (literal IMDS IP, decimal/octal/IPv6,
  redirects) so only the two-lookup TOCTOU gets through.
- **c5** public key deliberately unpublished → forces the `gcd(sᵢ^e − EMᵢ)`
  modulus recovery (reconstruct PKCS#1 v1.5 EM exactly) before the alg-confusion
  forge. Pure stdlib RSA. The hardest build.
- **c6** schema discovery is blind (introspection disabled); only one of several
  operations on `Invoice` misses the shop-ownership check; the admin field is
  behind a numeric guard brute-forced only via aliased batching in one request.

## Build order
1. Harness (shared Flask image + dispatcher, compose, scoreboard, Makefile). ✅ this turn
2. c1 settle, c2 ledger (theme centerpiece, pure logic) — this turn.
3. c3 rebate, c4 warehouse, c6 storefront — may delegate to per-challenge builder
   subagents against the fixed conventions.
4. c5 passport (crypto, correctness-critical) — build + test myself.
5. `make check` green end-to-end; iterate difficulty; write BRIEF/SOLUTION/DESIGN-NOTES/README; register in root README.
