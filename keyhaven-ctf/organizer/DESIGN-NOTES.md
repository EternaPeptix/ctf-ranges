# Design notes

## Why it's hard (not "find seven bugs")

1. **Seven unrelated deep models.** The whole point of this range (vs. the
   Flatpack web-CVE chain) is that no two stages share a mental model: an HTTP
   parser differential, XML-dsig reference-vs-position semantics, JWS key
   provenance, CBC padding-oracle math, the JS prototype chain, the YAML tag
   resolver, and lattice cryptanalysis. A solver has to genuinely learn seven
   different things; copy-paste won't carry you.
2. **The crypto is real, not cosmetic.** Stage 4 is a working byte-by-byte CBC
   oracle. Stage 7 has no shortcut: you must collect biased signatures, set up
   the Hidden Number Problem lattice, and run LLL to recover the key — the
   service refuses to sign the privileged manifest, so the key must be recovered.
3. **Concepts, not credentials.** Stage 2 is "a signature can be valid over text
   the app never reads"; stage 3 is "the verifier trusts a key the attacker
   supplied"; stage 7 is "biased randomness leaks the secret".
4. **Strict gating.** Only the edge is published. The internal services sit on an
   `internal: true` network and are reachable only through the `/gw` gateway,
   whose `kh_corp` cookie is issued *only* by a SAML-admin login, which is
   reachable *only* by smuggling. So stages 1→2 are a hard prerequisite for 3→7.

## Architecture

- **edge** (raw-socket, published): the TE/CL smuggling half + the authenticated
  `/gw/<svc>/*` reverse proxy. It is on both networks so it can reach the
  internal services, and validates the `kh_corp` HMAC cookie before proxying.
- **sso** (raw-socket): the lenient-framing smuggling backend + the SAML XSW SP.
  Issues the `kh_corp` cookie (shared `KH_CORP_SECRET` with the edge) on admin.
- **api** (Node): jwk-trusting JWT verify, the CBC capability oracle, and the
  `_.defaultsDeep` config merge; forwards enabled YAML imports to the vault.
- **vault** (Python, PyYAML 5.3.1): `full_load` on the imported manifest.
- **signer** (Python, `ecdsa`): biased-nonce ECDSA signing + the psychic-sig
  verifier.

## Faithfulness vs. safety

Each vuln reproduces the real CVE's mechanism (same missing check / same sink /
same math), re-implemented minimally because the vendor binaries aren't shipped.
All 7 CVEs were verified real against NVD + MITRE **and** confirmed absent from
CISA KEV (see `CVE-MAP.md`). Deliberately unsafe sinks (`eval`-equivalent YAML,
a key-recovery oracle, a smuggling desync) are contained to throwaway containers
on an internal-only network. **Never run this outside an isolated lab.**

Lab simplifications (documented in `CVE-MAP.md`): the smuggling is re-implemented
rather than a pinned HAProxy; stage 7 uses P-256 with a 64-bit nonce bias (vs.
PuTTY's 9-bit bias over P-521) so the lattice is solvable with ~8 signatures and
a pure-Python LLL in ~40–60s.

## Knobs for organizers

- **Harder stage 7:** reduce `BIAS` in `deploy/signer/app.py` (e.g. 16) and raise
  the collected-signature count `M` in the solver — closer to the real PuTTY
  regime, but the pure-Python LLL gets slower; consider `fpylll` for the solver.
- **Harder stage 2:** strip the hint text from `/internal/bootstrap` and
  `/internal/saml/sample` so the XSW position trick must be inferred.
- **Harder stage 4:** lengthen the sealed plaintext (more oracle queries) or make
  the two error responses look more alike (same status, subtly different body).
- **Flags** are plain strings in each service file; rotate before an event.
- **Port:** set `EDGE_PORT` in `.env` if 8080 is taken (the only published port).
- **Secret:** `KH_CORP_SECRET` (edge + sso) can be rotated; keep them equal.

## Known limitations

- `make check` runs the solver in a container that needs network access to
  `pip install ecdsa` once; after that it is cached.
- The minimal re-impls won't fingerprint byte-for-byte as the real vendor
  products beyond the advertised version strings.
- Stage 7's lattice solve is the slowest step (~40–60s) and is CPU-bound.
