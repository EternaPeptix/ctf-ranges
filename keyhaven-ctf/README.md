# Keyhaven CTF — "Null Cipher"

A **very hard, deeply-chained CTF** built from **7 real, pre-2026 CVEs that are
NOT on CISA's KEV catalog** — chosen because each requires an order-of-magnitude
better understanding to exploit than a typical web bug. The theme is a
*privacy-first SSO + secure-document vendor* whose own stack botches the hard
protocol and crypto details.

> ⚠️ Intentionally vulnerable training range. Run only on an isolated host you
> control. Every service contains a deliberately unsafe primitive, contained to
> throwaway containers on an internal-only Docker network. Do not deploy; do not
> point these techniques at anything you are not authorized to test.

Only the edge is published. Everything else lives on the internal `corp` network
with **no host ports** — you get in by smuggling a request past the edge, then
pivot through an authenticated gateway.

## The chain — seven distinct deep mechanisms (all verified non-KEV)

| # | CVE | Bug | What you must actually understand |
|---|-----|-----|-----------------------------------|
| 1 | **CVE-2019-18277** | HAProxy-class TE/CL request smuggling | an HTTP parser differential — two servers disagree on where a request ends |
| 2 | **CVE-2018-0489** | SAML XML signature wrapping (XSW) | XML canonicalization vs app-layer node resolution — a signature can validate over content the app never reads |
| 3 | **CVE-2018-0114** | node-jose `jwk` header injection | JWS key *provenance* — the verifier trusts a key embedded in the token itself |
| 4 | **CVE-2016-2107** | OpenSSL CBC padding oracle | CBC/CBC-R math — distinguishable padding-vs-MAC errors decrypt a secret |
| 5 | **CVE-2019-10744** | lodash `defaultsDeep` prototype pollution | the JS prototype chain — merging attacker keys flips a server-side default |
| 6 | **CVE-2020-14343** | PyYAML `full_load` RCE | the YAML tag resolver and its incomplete blacklist — a `type`/`extend`/`exec` gadget |
| 7 | **CVE-2024-31497** | biased-nonce ECDSA → Hidden Number Problem | lattice cryptanalysis — biased nonces leak the private key via LLL |

**Bonus:** **CVE-2022-21449** "Psychic Signatures" — a blank `(r,s)=(0,0)` ECDSA
signature validates against any key.

Flag format: `KH{...}`. Full provenance (NVD/MITRE + KEV checks) is in
[`organizer/CVE-MAP.md`](organizer/CVE-MAP.md).

## How the chain fits together

```
  smuggle past edge ACL ──▶ reach the internal SSO (/internal/*)        [stage 1]
  SAML signature-wrap ────▶ log in as admin, get the kh_corp cookie     [stage 2]
     the cookie unlocks the edge gateway: /gw/api, /gw/vault, /gw/signer
  forge a JWT (jwk) ──────▶ admin on the internal API                   [stage 3]
  padding oracle ─────────▶ decrypt a sealed capability                 [stage 4]
  prototype pollution ────▶ enable the YAML config importer             [stage 5]
  PyYAML full_load ───────▶ RCE on the document vault                   [stage 6]
  biased-nonce lattice ───▶ recover the master signing key → FINAL      [stage 7]
```

## Quick start

```bash
cp .env.example .env         # optional; edit EDGE_PORT if 8080 is taken
make up                      # build + start the whole range
```

- Edge (start here): `http://localhost:8080/`
- Everything else is corp-internal — smuggle in, SAML to admin, pivot via `/gw/*`.

Prove the whole thing solves (organizer self-check — drives all 7 stages through
the real smuggle→SAML→gateway path, including the lattice key recovery):

```bash
make check                   # runs the solver in a throwaway container; exits 0 iff all 7 land
```

Tear down:

```bash
make down
```

## Layout

```
keyhaven-ctf/
├─ docker-compose.yml        # edge (published) + sso/api/vault/signer (corp-internal)
├─ Makefile                  # up / up-edge / check / down / reset
├─ challenge/BRIEF.md        # hand this to players (scenario, scope, hints)
├─ deploy/
│  ├─ edge/                  # raw-socket proxy: TE/CL smuggling + the /gw gateway
│  ├─ sso/                   # raw-socket SSO: lenient framing + SAML XSW SP (stages 1–2)
│  ├─ api/                   # Node: jwk injection + CBC oracle + lodash pollution (3–5)
│  ├─ vault/                 # Python/PyYAML 5.3.1 full_load RCE (stage 6)
│  └─ signer/               # Python/ecdsa biased-nonce signer + psychic bonus (stage 7)
├─ scripts/verify.sh         # self-check wrapper
├─ scripts/solve.py          # the end-to-end solver (smuggle → SAML → gateway → all 7)
├─ scripts/hnp_solve.py      # standalone HNP/lattice key-recovery (stage 7)
└─ organizer/                # CVE-MAP · FLAGS · SOLUTION · DESIGN-NOTES
```

## What makes it hard

- **Seven unrelated deep models.** No stage is a harder version of a previous
  one: a parser differential, XML-dsig semantics, JWS key trust, CBC oracle math,
  the JS prototype chain, a YAML tag gadget, and a lattice attack. Solving the
  chain means genuinely learning seven different things.
- **The crypto is real.** Stage 4 is a working byte-by-byte padding oracle;
  stage 7 requires collecting biased signatures, building the HNP lattice, and
  running lattice reduction to recover the key — there is no password to guess.
- **You can't skip.** Only the edge is published; the internal services are
  reachable only after smuggling in and completing SAML, which issues the
  gateway cookie.

Full walkthrough with payloads: **[`organizer/SOLUTION.md`](organizer/SOLUTION.md)**.
