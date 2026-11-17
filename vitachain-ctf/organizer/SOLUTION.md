# VitaChain — full walkthrough

Every widget is a faithful minimal re-impl of a real, disclosed HackerOne report.
Reference exploit for all six is `scripts/solve.py` (pure stdlib, in-network).

---

## c1 — settle · a signed webhook that never binds amount ↔ order
*(CVE-2026-9189; H1 #682617)*

**Scheme.** `/pay/provider` models the external gateway: you really pay `amount`,
but — like a PayPal custom field — *you* choose the `invoice`. It returns a
payload `{invoice, amount, currency, payment_status:"paid", …}` and a genuine
HMAC signature. `/webhook/payment` verifies the HMAC, requires
`payment_status=="paid"`, requires the currency to match the order, then settles
`orders[invoice]`.

**Flaw.** It never compares `amount` to the order total. The signature is real,
so you can't forge — but you don't need to.

**Exploit.**
```
oid  = POST /order/create {sku:"vip"}          # a $5,000 order
conf = POST /pay/provider {invoice:oid, amount:1, currency:"USD"}
POST /webhook/payment {payload:conf.payload, signature:conf.signature}
GET  /order/<oid>                              # status: paid -> flag
```

**Lesson.** Authenticating a webhook (origin) is not validating it (does this
payment cover *this* order?). Bind amount + currency + recipient to the order.

---

## c2 — ledger · credited an on-chain deposit from a reverted transaction
*(H1 #300748, Coinbase)*

**Scheme.** A mock chain: a *non-reverting* tx must be covered by the sender's
balance (you can't mint money), but any tx may *revert* — its state rolls back
while `debug_traceTransaction` still lists the attempted internal transfers.
`/deposit/scan` sums the trace transfers to your deposit address and credits them.

**Flaw.** `scan` never checks `receipt_status`. A reverted tx moves no money yet
still has traces.

**Exploit.**
```
dep = GET /.deposit_address
tx  = POST /chain/broadcast {transfers:[{to:dep, value:5000}], revert:true}
POST /deposit/scan {txhash:tx}                 # credits 5000 from a reverted tx
POST /buy {sku:"vip"}                           # flag
```

**Lesson.** On-chain finality = the top-level receipt `status == success`. Trace
transfers alone are "attempted," not "settled."

---

## c3 — rebate · redemption is check-then-mark with no atomicity
*(H1 #759247 Reverb; #1717650 Stripe)*

**Scheme.** A $25 single-use card; VIP costs $100. `/redeem` checks `used`, waits
out a settlement window, credits the balance, *then* marks `used`.

**Flaw.** The `used` flag is set too late and without synchronization. K
concurrent redemptions all pass the `used?` check before any sets it.

**Exploit.** Fire ~12 `/redeem` of the one card concurrently (a `threading.Barrier`
makes them land together), each credits $25 → balance ≥ $100 → `/buy vip`. A
single serial request always behaves; only the race breaks it.

**Lesson.** Redeem/spend must be one atomic compare-and-set (DB transaction,
`UPDATE … WHERE used=false` row lock, or `SELECT … FOR UPDATE`).

---

## c4 — warehouse · SSRF to IMDS via a DNS-rebind TOCTOU
*(H1 #1369312 Concrete CMS; #632101 GitLab)*

**Scheme.** `/fetch?url=` imports a URL server-side. The validator resolves the
host and rejects anything not globally public — and it genuinely blocks every
*static* bypass: the literal IMDS IP, `127./10./192.168./172.16-31.*`, `0.0.0.0`,
decimal/octal/hex integer IPs, IPv6 (`::1`, `::ffff:169.254.169.254`, `fd00::/8`),
internal names, and redirects.

**Flaw.** It resolves the host **twice** — once to validate (time-of-check), once
to connect (time-of-use) — and trusts they agree.

**Exploit.** Register an attacker DNS record that answers a public IP first, then
`imds` (TTL 0): validation sees the public IP and passes; the fetch re-resolves
and dials `imds`. Read `…/iam/security-credentials/<role>`; the `SecretAccessKey`
is the flag. (Re-register before each fetch — the flip's last answer repeats.)

**Lesson.** Resolve once and connect to *that pinned IP*; re-validate the final
socket address; isolate the metadata endpoint.

---

## c5 — passport · recover the RSA public key from signatures, then confuse the alg
*(H1 #1210502, Jitsi/8x8)*

**Scheme.** JWT verify accepts RS256 (RSA, against the server's public key) and
HS256 (HMAC with the **PEM public key** as the secret) — the classic
algorithm-confusion bug. But the public key is **not published** (no JWKS), so
you can't just HMAC with it. The public exponent is small (`e = 3`), and `/token`
is an RS256 signing oracle.

**Flaw + exploit.** For each token, `s = EM^d mod N`, so `s^e ≡ EM (mod N)` and
`N | (s_i^e − EM_i)` as integers (`EM_i` = the PKCS#1 v1.5 EMSA encoding of
`SHA-256(signing_input)`, whose length `k` equals the signature length):
```
N = gcd(s_1^e − EM_1, s_2^e − EM_2, …)        # strip small factors
```
With `e=3` the `s^3` integers are small and the gcd is instant. Rebuild the
SubjectPublicKeyInfo DER/PEM from `(N, e)` (standard encoding → byte-identical to
the server's), then forge `{"alg":"HS256"}` / `{"role":"admin"}` signed with
`HMAC-SHA256(PEM, signing_input)`. `/admin` → flag.

**Lesson.** Never let one key serve two algorithms; pin exactly one `alg`. (And a
small `e` plus a signing oracle leaks the "public" modulus you tried to hide.)

---

## c6 — storefront · GraphQL BOLA via opaque IDs + alias-batching past the limiter
*(H1 #2207248 Shopify; #2166697 HackerOne)*

**Scheme.** `POST /graphql`. Introspection is off; node IDs are opaque
`base64("gid://vitachain/Invoice/<n>")`. `invoice(id)` enforces shop ownership;
`receipt(id)` resolves the same id with **no** ownership check (BOLA). A rate
limiter allows 8 **HTTP requests** per 10s.

**Flaw.** Two things compound: only one of the two Invoice fields checks
ownership, and the limiter counts requests, not operations.

**Exploit.** Decode your own gid (from `myInvoice`) to learn the scheme. The
admin invoice's id is a small number you can't guess and serial brute is
throttled — so send **one** request aliasing `receipt(id)` across n=0..999. It
costs a single rate-limit tick and one alias returns the admin receipt body with
the flag.

**Lesson.** Enforce object-level authz on *every* field that resolves an object;
never treat an opaque id as a capability; rate-limit by resolved operations.

---

## Reproduce
```bash
make up
make check        # scripts/solve.py in a throwaway container on vitachain_net; exit 0
make down
```
Secrets are random per boot; the exploits recover or sidestep them each run, so
`make reset && make check` stays green, and `make check` is safe to re-run.
