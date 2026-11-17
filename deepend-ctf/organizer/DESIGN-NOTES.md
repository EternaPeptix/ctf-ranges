# Design notes

## The brief: overlap of (1) difficult, (2) H2 2026, (3) novel technique

Each challenge had to satisfy all three at once. That is a narrow intersection,
so this range is **deep, not wide** — six challenges, each a *different*
research-grade exploitation technique, where recognising and implementing the
technique is the whole difficulty.

| # | Why it's hard | Why it's novel |
|---|---------------|----------------|
| 1 | you must understand Go's `net/url` opaque parsing and that the proxy forwards it | parser differential via `URL.Opaque`, not path traversal |
| 2 | spot that signing and processing use different name canonicalisation | redirect-binding name differential, not XML-sig-wrapping |
| 3 | understand ECDSA adaptor signatures well enough to forge an unbound pre-sig | attacks a bleeding-edge scriptless-scripts primitive |
| 4 | implement GF(2¹²⁸) and the Joux forbidden attack | nonce-reuse tag forgery over the GCM field |
| 5 | find that a templating feature bypasses the sandbox's accessor | Formatter field-resolution gadget |
| 6 | realise the validator and extractor parse different headers | "zip cloaking" TOCTOU between two parsers |

Two of the six (c3, c4) are **full scripted crypto breaks** in the solver — no
oracle hands you the answer; you recover a key / forge a signature.

## Architecture
- Heterogeneous on purpose: a **Go** reverse proxy (c1), a **Rust** service (c6),
  and four **Python** services (c2–c5), each its own container.
- `scripts/solve.py` runs all six in-network (by service name); it ships a
  hand-rolled GF(2¹²⁸) field and the adaptor-signature forgery, and needs only
  `ecdsa` installed (for c3) — nothing else beyond stdlib.
- A small Flask scoreboard lists the six and checks flags.

## Fidelity vs. safety
Each reproduces the real CVE's technique (see `CVE-MAP.md` for per-challenge
simplifications — notably c4 uses single-block messages so key recovery is a
unique square root, and c1 is the *actual* Go opaque-parse behaviour). Unsafe
primitives (a nonce-reusing GCM, a forgeable verifier, a sandbox bypass, a
header-mismatched extractor) are contained to throwaway containers. **Do not
deploy.**

## Knobs for organizers
- **Harder c4:** use multi-block messages (key recovery becomes a GF(2¹²⁸)
  polynomial factorisation, not a square root).
- **Harder c3:** require a DLEQ proof field and only skip *part* of its check.
- **Swap a category:** `CVE-MAP.md` lists a verified H2-2026 bench (Netty H1→H2,
  Next.js fetch-cache smuggling, OpenSSL EC lattice/HNP, wolfSSH curve confusion,
  vm2 escape, point-at-infinity forgery, …).
- **Ports:** 8401–8406 + scoreboard 8400; edit `docker-compose.yml` if taken.

## The series
- **Flatpack** — 10 real 2026 CVEs, chained, hard to exploit.
- **Keyhaven** — 7 deep non-KEV CVEs, chained, hard to execute (lattice/padding).
- **Dropspot** — obvious-once-you-look bugs.
- **Bastion** — hard-to-find / trivial-to-exploit needles.
- **The Backlog** — 15 H2-2026 CVEs, jeopardy breadth.
- **The Deep End** — 6 H2-2026 CVEs at the difficult × novel-technique frontier (this one).
