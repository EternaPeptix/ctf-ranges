# Bastion CTF — "Military-grade security."

A **hard web/crypto CTF** built on one idea: every flag sits behind a single
**non-obvious insight** that is brutal to discover black-box, and a *one-liner
once you know it.* The app looks airtight — no exposed `.git`, no debug mode, no
obvious anything. The difficulty is entirely in *seeing the needle.*

> ⚠️ Intentionally vulnerable training app. Run only on an isolated host you
> control. Do not deploy.

## The five needles

| # | Insight (hard to spot) | Exploit (trivial once known) |
|---|------------------------|------------------------------|
| 1 | the landing page carries **zero-width characters** | filter U+200B/U+200C, read the bits |
| 2 | the reserved-name block uses `lower()` but the admin check uses **NFKC** | register `ᴬdmin` (U+1D2C) — slips the block, normalizes to admin |
| 3 | the session cookie is **AES-ECB** | cut-and-paste ciphertext blocks to forge `role=admin` (Cryptopals 13) |
| 4 | request signatures are **md5(secret ‖ data)** | length-extend a known pair to append `admin=1` |
| 5 | the preview allowlist uses **`re.search` with no anchors** | any URL *containing* `bastion.internal` is fetched → SSRF to the localhost flag |

Flag format: `BAS{...}`.

## Quick start

```bash
cp .env.example .env         # optional; edit WEB_PORT if 8080 is taken
make up
```

- App: `http://localhost:8080/`

Prove it all solves (organizer self-check — needs only `python3`, no pip):

```bash
make check                   # runs scripts/solve.py; exits 0 iff all 5 flags land
```

Tear down:

```bash
make down
```

## Layout

```
bastion-ctf/
├─ docker-compose.yml        # one container
├─ Makefile                  # up / check / down / reset
├─ challenge/BRIEF.md        # hand this to players
├─ deploy/web/{Dockerfile,app.py}
├─ scripts/solve.py          # the solver (ECB cut-paste + hand-rolled MD5 length ext)
├─ scripts/verify.sh         # self-check wrapper
└─ organizer/                # FLAGS · SOLUTION · DESIGN-NOTES
```

## Why it's hard (and fair)

Nothing here is a password to brute or a filter to fuzz for hours. Each flag is a
textbook technique — you either recognize the *tell* (invisible characters, a
block-aligned ciphertext, an `md5(secret‖…)` tag, a regex without `$`) or you
don't. Once you do, the exploit is a handful of lines. The app hands you exactly
what each technique needs (a valid signed pair, an encrypting oracle, a preview
proxy) and nothing more. Great for teaching people to **recognize the shape of a
vulnerability.**

Full walkthrough: **[`organizer/SOLUTION.md`](organizer/SOLUTION.md)**.
