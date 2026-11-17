# CTF Ranges

A collection of **14 self-contained, automatically-verifiable CTF ranges** —
each one a small, themed security playground you can stand up with Docker in a
couple of commands. Every range re-implements real vulnerability classes
(faithful, minimal, isolated), ships an automated solver, and proves itself
end-to-end.

Every range follows the same contract:

```bash
cd <range>-ctf
make up        # build + start the services
make check     # run the solver in-network and capture every flag — exit 0
make down      # tear it all down
```

`make check` is the guarantee: it runs the reference exploit for every challenge
on the challenge network and only exits 0 when all flags are captured. If it's
green, the range is solvable exactly as shipped.

---

## The ranges

### Web applications
| Range | Theme | Highlights |
|-------|-------|------------|
| [`dropspot-ctf`](dropspot-ctf) | "Ship fast, audit never" — the facepalm bugs | exposed `.git`, IDOR, `alg:none` JWT, `X-Forwarded-For` trust, mass assignment, debug flag, backup in webroot |
| [`bastion-ctf`](bastion-ctf) | "Military-grade" — needles that are brutal to find, trivial to exploit | zero-width stego, NFKC normalization bypass, ECB cut-and-paste, MD5 length extension, unanchored-regex SSRF |
| [`backlog-ctf`](backlog-ctf) | A jeopardy board of **15 independent H2-2026 CVEs** | SQLi, SSTI, SSRF, LFI, upload-RCE, arg-injection, XXE, IDOR, JWT, Kong authz, pickle deser, PHP object injection, AI config RCE, agent abuse, non-HTTP RESP |

### Cryptography & protocols
| Range | Theme | Highlights |
|-------|-------|------------|
| [`keyhaven-ctf`](keyhaven-ctf) | A "privacy-first" vendor that botches its own crypto — a 7-stage chain | HTTP request smuggling, SAML signature wrapping, JWK header injection, CBC padding oracle, prototype pollution, PyYAML RCE, biased-nonce lattice (HNP) key recovery |
| [`deepend-ctf`](deepend-ctf) | Six research-grade H2-2026 techniques where the *method* is the puzzle | Traefik `URL.Opaque` desync, SAML redirect canonicalization diff, ECDSA adaptor-signature forgery, AES-GCM forbidden attack, RestrictedPython sandbox escape, Rust `zip2` cloaking |

### Smart contracts / DeFi (EVM)
| Range | Theme | Highlights |
|-------|-------|------------|
| [`reentrant-ctf`](reentrant-ctf) | A DeFi protocol, thoroughly *rekt* | reentrancy, flash-loan oracle manipulation, unprotected initializer, signature replay, proxy storage collision, ERC-4626 inflation |
| [`delphi-ctf`](delphi-ctf) | Everything that goes wrong when you **trust a price** | Chainlink `minAnswer` clamp, stale feed, short-window TWAP, read-only reentrancy, naive LP pricing, decimals confusion |
| [`gauntlet-ctf`](gauntlet-ctf) | The hardest range — research-grade EVM/crypto primitives | ECDSA nonce reuse, Merkle second-preimage, `ecrecover==0`, **EIP-1153** transient-storage reentrancy, weak randomness, selector/facet hijack, **BN254 pairing-verifier forgery** |

### AI / agentic
| Range | Theme | Highlights |
|-------|-------|------------|
| [`puppeteer-ctf`](puppeteer-ctf) | Turn an agentic AI assistant against its owner | ingestion prompt injection, gateway SSRF, MCP tool command injection, RAG cross-tenant IDOR, model-load config-class RCE, memory IDOR |

### Infrastructure
| Range | Theme | Highlights |
|-------|-------|------------|
| [`audit-ctf`](audit-ctf) | A database & SSH security audit | PostgreSQL `COPY FROM PROGRAM` RCE, MySQL `FILE`/`LOAD_FILE`, SQLite UNION injection, leaked SSH key, and a log-forensics challenge |
| [`cumulus-ctf`](cumulus-ctf) | One cloud breach, start to finish | SSRF → IMDS credential theft → S3 bucket misconfig → IAM `CreatePolicyVersion` privesc → EKS/Kubernetes secrets |
| [`teardown-ctf`](teardown-ctf) | Binary exploitation & reverse engineering | ret2win overflow, format string, ROP → `system`, an RE crackme, and a modern heap **tcache safe-linking** poison |

### Original synthesis (no CVEs)
| Range | Theme | Highlights |
|-------|-------|------------|
| [`obscura-ctf`](obscura-ctf) | "Provably secure. Allegedly." — five **original** flaws invented from first principles, no CVE/PoC; **very hard** | deterministic-nonce Schnorr → linear key recovery, Fiat–Shamir without commitment binding, authorize-before-normalize path traversal, keystream reuse via a label-length KDF, bytecode verifier/VM overlapping-instruction escape |

### E-commerce & crypto payments (HackerOne reports)
| Range | Theme | Highlights |
|-------|-------|------------|
| [`vitachain-ctf`](vitachain-ctf) | A vitamin shop with on-chain checkout — six real **disclosed HackerOne reports** at the web ↔ crypto-payment seam; **extremely hard** | signed-webhook amount-binding bypass, reverted-transaction deposit credit, gift-card redemption race, SSRF → IMDS via DNS-rebind TOCTOU, RSA-pubkey-recovery → RS256/HS256 JWT confusion, GraphQL BOLA + alias-batching past the rate limiter |

---

## How it's built

- **One harness, many domains.** Most ranges are a `docker-compose` of small
  faithful service re-implementations plus a scoreboard and a solver. The EVM
  ranges run a local `anvil` chain and a Foundry project; `teardown` serves real
  x86-64 pwnables over `socat`.
- **Flags are earned.** On-chain ranges release a flag only after verifying
  `isSolved()` on-chain; service ranges capture flags by actually exploiting.
  Solutions live under each range's `organizer/`.
- **Self-verifying.** Every range's `make check` is CI-ready: it either captures
  all flags and exits 0, or it fails loudly.

## ⚠️ Disclaimer

Every service, contract and binary here is a **deliberately vulnerable training
artifact** — including intentional "secrets" (test keys, fake credentials) that
are part of the challenges. Run these only in isolation. **Do not deploy any of
it to a real network**, and don't reuse any key or credential from this repo.
