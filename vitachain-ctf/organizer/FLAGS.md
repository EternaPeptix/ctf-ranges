# Flags (organizer)

All 6 verified live via `scripts/solve.py` (RESULT: ALL 6 FLAGS CAPTURED, exit 0),
and the self-check is repeatable (`make check` can be run back-to-back).

| # | Port | Widget | Flag | One-line exploit |
|---|------|--------|------|------------------|
| 1 | 8701 | settle | `FLAG{settle_signed_webhook_never_bound_the_amount_4c1a7e}` | create a `vip` order; `/pay/provider` with `invoice=<that order>`, `amount=1`; POST the signed confirmation to `/webhook/payment` |
| 2 | 8702 | ledger | `FLAG{ledger_credited_a_reverted_transaction_b9f330}` | `/chain/broadcast {transfers:[{to:<deposit>,value:5000}], revert:true}`; `/deposit/scan`; `/buy vip` |
| 3 | 8703 | rebate | `FLAG{rebate_check_then_credit_is_not_atomic_2e7d64}` | fire ~12 concurrent `/redeem` of the one card (barrier-synced); then `/buy vip` |
| 4 | 8704 | warehouse | `FLAG{warehouse_dns_rebind_toctou_imds_7a21e9}` | `/dns/register {host, answers:[<public ip>, "imds"]}`; `/fetch?url=http://<host>/latest/meta-data/iam/security-credentials/<role>` (re-register per fetch) |
| 5 | 8705 | passport | `FLAG{passport_rsa_pubkey_from_sigs_then_hs256_d15ea5}` | collect ≥2 RS256 tokens from `/token`; `N = gcd(sᵢ³ − EMᵢ)`; rebuild SPKI PEM; forge `alg:HS256` `{role:admin}` HMAC'd with the PEM; `/admin` |
| 6 | 8706 | storefront | `FLAG{storefront_opaque_ids_batched_past_the_limit_88c0de}` | one `/graphql` POST with `aₙ: receipt(id:"<gid n>"){body}` aliased over n=0..999 → one alias returns the admin receipt body |

## Where the flags live
- **settle / ledger / rebate / passport** — `FLAG = ...` in each `app/challenges/cN_*.py`.
- **warehouse** — the flag is the `SecretAccessKey` served by the internal **`imds`**
  container; it is captured only by actually reaching that host through the rebind,
  never from the c4 process (the c4 module defines no FLAG).
- **storefront** — in the admin invoice body (`s_ops` tenant), reachable only via the
  BOLA `receipt` field.

## Based on (real, disclosed HackerOne reports / CVEs)
| # | Report(s) |
|---|-----------|
| 1 | CVE-2026-9189 (CF7 PayPal/Stripe add-on); H1 #682617 (Starbucks callback forgery) |
| 2 | H1 #300748 (Coinbase — ETH balance manipulation via reverted tx traces) |
| 3 | H1 #759247 (Reverb gift-card race); #1717650 (Stripe promo-limit TOCTOU) |
| 4 | H1 #1369312 (Concrete CMS) + #632101 (GitLab) — SSRF via DNS rebinding |
| 5 | H1 #1210502 (Jitsi/8x8 JWT key confusion) + RSA-pubkey-from-signatures |
| 6 | H1 #2207248 (Shopify GraphQL BOLA) + #2166697 (HackerOne alias batching) |

## Scoring suggestion
All six demand a derived exploit (not a recognized tell). Suggested weights by
depth of derivation:

| Widget | Why | Points |
|--------|-----|--------|
| settle | pure logic: amount↔order binding | **250** |
| ledger | finality/receipt-status reasoning + craft a reverting tx | **300** |
| rebate | spot missing atomicity + land a real concurrent race | **300** |
| storefront | opaque-id BOLA + realize the limiter counts requests → alias-batch | **350** |
| warehouse | defeat an airtight static filter → DNS-rebind TOCTOU | **400** |
| passport | recover an unpublished RSA modulus from signatures, then alg-confusion | **450** |

## Notes
- `make check` runs every exploit from a throwaway `python:3.12-slim` container on
  `vitachain_net`, reaching widgets by service name (`c1`..`c6`, `imds`). Pure stdlib.
- Secrets are random per boot (provider HMAC key, RSA key, admin invoice id, deposit
  address); the exploits recover or sidestep them each run, so `make reset && make
  check` stays green with fresh secrets.
- The host's Docker default address pools were exhausted by sibling ranges, so the
  compose pins `vitachain_net` to an explicit `10.84.0.0/24`.
