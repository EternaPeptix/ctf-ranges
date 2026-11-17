# VitaChain CTF — "Premium supplements. On-chain checkout."

An **extremely hard** jeopardy board of six challenges for a vitamin shop that
takes crypto — each a faithful minimal re-implementation of a **real, publicly
disclosed HackerOne report**. The bugs are real; there is no write-up that names
*this* app. Every flag needs a correct, derived exploit — no brute force, no
fuzzing. The theme is the **web ↔ crypto-payment seam**: how an off-chain backend
trusts, verifies, and races against on-chain money and against itself.

> ⚠️ Intentionally vulnerable training widgets with intentional "secrets" (test
> keys, a mock IMDS credential). Run only on an isolated host you control. Do not deploy.

## The six widgets

| # | Widget | Based on (disclosed H1) | Flaw | Exploit (short, once known) |
|---|--------|-------------------------|------|------------------------------|
| 1 | **settle** | CVE-2026-9189 / H1 #682617 | signed payment webhook never binds **amount ↔ order** | pay $1 tagged to the $5,000 `vip` invoice; the genuine signature settles it |
| 2 | **ledger** | H1 #300748 (Coinbase) | deposit indexer credits trace transfers, ignores **receipt status** | broadcast a pay-then-**revert** tx; scan credits it; buy VIP |
| 3 | **rebate** | H1 #759247 / #1717650 | redemption is **check-then-mark**, non-atomic | fire ~12 concurrent redeems of one card → 4× credit → VIP |
| 4 | **warehouse** | H1 #1369312 / #632101 | URL filter resolves to **validate**, resolves again to **fetch** | register a DNS rebind (public → `imds`); `/fetch` dials IMDS, leaks creds |
| 5 | **passport** | H1 #1210502 | RS256/HS256 confusion, **public key unpublished** | recover `N = gcd(sᵢ³ − EMᵢ)` from `/token`, rebuild PEM, forge HS256 admin |
| 6 | **storefront** | H1 #2207248 / #2166697 | GraphQL **BOLA** on opaque ids + limiter counts **requests** | one request aliasing `receipt(id)` over 0..999 → admin receipt |

Flag format: `FLAG{...}`.

## Quick start
```bash
cp .env.example .env         # optional; edit SB_PORT if 8700 is taken
make up
```
- Scoreboard: `http://localhost:8700/`
- Widgets:    `http://localhost:8701 .. 8706`

Prove it all solves (organizer self-check — runs in a throwaway container on the
challenge network, pure `python3` stdlib, no pip):
```bash
make check                   # runs scripts/solve.py; exits 0 iff all 6 flags land
```
Tear down:
```bash
make down
```

## Layout
```
vitachain-ctf/
├─ docker-compose.yml        # 6 widgets + scoreboard + internal imds helper
├─ Makefile                  # up / check / down / reset
├─ challenge/BRIEF.md        # hand this to players
├─ app/
│  ├─ Dockerfile
│  ├─ serve.py               # dispatch by $CHALLENGE
│  ├─ common.py              # shared helpers (HMAC, base64url)
│  └─ challenges/cN_*.py     # settle · ledger · rebate · warehouse · passport · storefront
├─ imds/{Dockerfile,app.py}  # internal-only mock metadata service (c4 target)
├─ scoreboard/{Dockerfile,app.py}
├─ scripts/solve.py          # the 6 reference exploits (stdlib, in-network)
├─ scripts/verify.sh         # self-check wrapper
└─ organizer/                # FLAGS · SOLUTION · DESIGN-NOTES · LINEUP
```

## Why it's hard (and fair)
Each widget wears a convincing disguise: a verified signature (settle), an
airtight static SSRF filter (warehouse), disabled introspection and opaque ids
(storefront), an unpublished public key (passport), a balance-enforcing chain
(ledger), a single-use card (rebate). The difficulty is in *deriving* the one
thing each one got wrong — and the reference solver proves it by doing the real
work (winning a race, driving a DNS rebind, recovering a 1024-bit RSA modulus).
Secrets are random per boot, so `make reset && make check` stays green and the
self-check is safe to re-run.

Full walkthrough with derivations: **[`organizer/SOLUTION.md`](organizer/SOLUTION.md)**.
Design rationale and H1 mapping: **[`organizer/DESIGN-NOTES.md`](organizer/DESIGN-NOTES.md)** · **[`organizer/LINEUP.md`](organizer/LINEUP.md)**.

> Note: the host's default Docker address pools can be exhausted by sibling ranges;
> this compose pins `vitachain_net` to an explicit `10.84.0.0/24` to coexist.
