# VitaChain — "Premium supplements. On-chain checkout."

> Difficulty: **Extremely hard** · Category: Crypto-payment / Web / Auth / API · Flags: 6
> Everything here is an isolated lab. Only attack the VitaChain widgets.

## Scenario

**VitaChain** sells supplements and takes crypto at checkout. Six services, built
in-house. Each one is a faithful re-implementation of a **real, publicly
disclosed HackerOne report** — so the bug is real, but there is no write-up that
names *this* app. Each flag needs a correct, derived exploit: no brute force, no
fuzzing, no recon rabbit holes. The board is at `http://localhost:8700/`.

## The widgets

| # | Port | Widget | Claims to do |
|---|------|--------|--------------|
| 1 | 8701 | **settle** | confirm orders from a signed crypto-payment webhook |
| 2 | 8702 | **ledger** | credit store balance from on-chain deposits |
| 3 | 8703 | **rebate** | redeem a single-use gift card for store credit |
| 4 | 8704 | **warehouse** | import a product image from a URL |
| 5 | 8705 | **passport** | passwordless JWT single-sign-on |
| 6 | 8706 | **storefront** | a GraphQL API over your invoices |

Flag format: `FLAG{...}`. There are 6. The goal in each shop is the same: become
a paid VIP / admin without paying or being one.

## Hints (one per flag — open only if stuck)

<details><summary>1 — settle</summary>
The webhook signature is genuine, the currency is checked, the status must be
<code>paid</code>. So what is <em>not</em> checked? You choose the <code>invoice</code> when you pay. What
stops a $1 payment from settling a $5,000 order?
</details>

<details><summary>2 — ledger</summary>
A non-reverting transaction has to be covered by your balance — you can't mint
money that way. But a transaction can revert. What does the deposit indexer read:
the top-level receipt, or the internal transfer traces? What do traces still show
for a transaction that rolled back?
</details>

<details><summary>3 — rebate</summary>
One honest redemption gives you a quarter of VIP. The card is single-use… checked
how, and <em>when</em>? A single request always behaves. What about twenty at once,
landing inside the same settlement window?
</details>

<details><summary>4 — warehouse</summary>
The import filter is airtight against every single-URL trick — IMDS IP, decimal/
octal/hex/IPv6 encodings, redirects. Give up on finding one string that slips
through. The server resolves your host to validate it, and resolves it <em>again</em> to
fetch it. What if your DNS answers differently the second time?
</details>

<details><summary>5 — passport</summary>
The verifier takes RS256 and HS256. The HS256 key confusion only works if you
have the exact public-key bytes — and there is no JWKS. But <code>/token</code> hands out
RS256 signatures, and the exponent is small. For each signature,
<code>s^e ≡ EM (mod N)</code>, so <code>N</code> divides <code>s^e − EM</code>. Two signatures, a gcd, and you
have the modulus; rebuild the PEM and forge an HS256 admin token with it.
</details>

<details><summary>6 — storefront</summary>
Introspection is off and the invoice IDs are opaque — but decode one (it's your
own, from <code>myInvoice</code>) and it is just <code>base64("gid://vitachain/Invoice/&lt;n&gt;")</code>.
Two fields take an invoice id; only one checks that it's yours. The admin's id is
a small number you can't guess, and the limiter throttles you after a few tries —
unless one request can carry a thousand aliased lookups.
</details>

## Scope / legal

Intentionally vulnerable training widgets with intentional "secrets" (test keys,
a mock IMDS credential). Run only on an isolated host you control. Do not deploy,
and do not point these techniques at systems you are not authorized to test.
