# The Deep End — CTF range

Six **black-belt** challenges at the intersection the brief asked for: **genuinely
hard to exploit × published in H2 2026 × a novel technique**. Each one is a
different *research-grade* exploitation method — the technique is the whole
puzzle, not another OWASP top-10 bug. Independent challenges; a scoreboard checks
flags.

> ⚠️ Intentionally vulnerable training range. Run only on an isolated host you
> control. Every service contains a deliberately unsafe primitive. Do not deploy.

## The six

| # | Technique (what's novel) | CVE (publ.) | Product | The break |
|---|--------------------------|-------------|---------|-----------|
| 1 | **Proxy routing↔forwarding desync** | CVE-2026-88009 (09-16) | Traefik | Go `net/url` stores a rootless target in `URL.Opaque`; ACL runs on `URL.Path` (`/`) but `Opaque` is forwarded → reach the internal `/admin` route |
| 2 | **Auth-protocol canonicalization differential** | CVE-2026-117691 (11-05) | Keycloak | SAML redirect binding signs the *literal* param name but processes the *decoded* one → `%53AMLResponse` carries an unsigned admin assertion |
| 3 | **Adaptor-signature forgery** | CVE-2026-55174 (09-30) | UltrafastSecp256k1 | ECDSA adaptor pre-sig verify never binds `r` to the adaptor point → existentially forge a pre-signature with the public key alone |
| 4 | **GF(2¹²⁸) tag forgery** | CVE-2026-81020 (08-28) | wolfEngine | AES-GCM nonce reuse → **forbidden attack**: recover the GHASH key `H` (unique square root over GF(2¹²⁸)), forge a valid tag |
| 5 | **Sandbox escape via a new gadget** | CVE-2026-76825 (09-16) | RestrictedPython | `str.format` field resolution walks `__class__→__init__→__globals__` past the sandbox's guarded accessor → read hidden globals |
| 6 | **File-format parser differential (TOCTOU)** | CVE-2026-115905 (10-26) | Rust `zip2` | "zip cloaking": the validator reads Central-Directory names, the extractor reads Local-File-Header names → a file the validator never approved gets written |

All verified **published H2 2026** (NVD + MITRE). Flag format: `0DAY{...}`. Full
provenance: [`organizer/CVE-MAP.md`](organizer/CVE-MAP.md).

## Quick start

```bash
cp .env.example .env         # optional
make up                      # build all 6 + scoreboard (Go + Rust + Python; Rust ~1-2 min)
```

- Scoreboard: `http://localhost:8400/`
- Challenges: `http://localhost:8401` .. `8406`

Prove it all solves (organizer self-check — runs all 6 exploits in-network, incl.
the GF(2¹²⁸) GCM forgery and the adaptor-signature forgery):

```bash
make check                   # exits 0 iff all 6 flags land
```

Tear down:

```bash
make down
```

## Layout

```
deepend-ctf/
├─ docker-compose.yml        # scoreboard + c1..c6
├─ Makefile                  # up / check / down / reset
├─ challenges/
│  ├─ c1-traefik-opaque/     # Go reverse proxy (URL.Opaque desync)
│  ├─ c2-saml-canon/         # Python (SAML %-name differential)
│  ├─ c3-adaptor-sig/        # Python/ecdsa (adaptor-signature forgery)
│  ├─ c4-gcm-forbidden/      # Python (GCM nonce-reuse)
│  ├─ c5-restrictedpython/   # Python (Formatter escape)
│  └─ c6-zip-cloak/          # Rust/tiny_http (zip cloaking)
├─ scoreboard/               # Flask board + flag checker
├─ scripts/solve.py          # all 6 solvers (incl. hand-rolled GF(2^128) + adaptor forgery)
├─ scripts/verify.sh
└─ organizer/                # CVE-MAP · FLAGS · SOLUTION · DESIGN-NOTES
```

Full walkthrough: **[`organizer/SOLUTION.md`](organizer/SOLUTION.md)**.
