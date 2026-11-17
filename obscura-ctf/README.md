# Obscura CTF — "Provably secure. Allegedly."

A **very hard, original** jeopardy board of five vulnerabilities **invented from
first principles** — no CVE, no public PoC, no write-up to find. Each widget uses
real primitives correctly *except for one deliberate design decision*; the whole
difficulty is in **deriving** the attack. Brutal black-box, a handful of lines
once you see it.

> ⚠️ Intentionally vulnerable training widgets with intentional "secrets" (test
> keys). Run only on an isolated host you control. Do not deploy.

## The five widgets

| # | Widget | Looks like | Original flaw | Exploit (short, once known) |
|---|--------|-----------|---------------|------------------------------|
| 1 | **reverb** | Schnorr sigs with "reproducible" nonces | nonce `k_i = seed·r^i` with `r` public → nonces **linearly dependent** | 2 sigs → solve 2×2 system mod q for `d` → forge `grant-admin` |
| 2 | **echo** | passwordless zero-knowledge login | Fiat–Shamir challenge omits the commitment `t` | pick `z`, set `t=g^z·Y^(−e)` → valid proof with **no** secret |
| 3 | **warden** | HMAC-signed, scoped download links | authorize + sign the **raw** path; decode/normalize only at fetch | sign `/public/%2e%2e/admin/flag.txt` → resolves to `/admin/flag.txt` |
| 4 | **tally** | one-time "sealed envelope" encryption | keystream keyed on **`len(label)`** only → two-time pad | seal `00…` under a 5-char label → that's the keystream → XOR admin ct |
| 5 | **cage** | verified sandbox for untrusted bytecode | verifier checks jump **bounds**, not **alignment** | `PUSH 0x20 ; JMP 1` → VM runs the hidden `READFLAG` |

Flag format: `FLAG{...}`.

## Quick start

```bash
cp .env.example .env         # optional; edit SB_PORT if 8600 is taken
make up
```

- Scoreboard: `http://localhost:8600/`
- Widgets:    `http://localhost:8601 .. 8605`

Prove it all solves (organizer self-check — runs in a throwaway container on the
challenge network, pure `python3` stdlib, no pip):

```bash
make check                   # runs scripts/solve.py; exits 0 iff all 5 flags land
```

Tear down:

```bash
make down
```

## Layout

```
obscura-ctf/
├─ docker-compose.yml        # 5 widgets + scoreboard, one shared image
├─ Makefile                  # up / check / down / reset
├─ challenge/BRIEF.md        # hand this to players (includes the cage ISA)
├─ app/
│  ├─ Dockerfile
│  ├─ serve.py               # dispatch by $CHALLENGE
│  ├─ common.py              # shared Schnorr group (RFC 3526 2048-bit safe prime)
│  └─ challenges/cN_*.py     # reverb · echo · warden · tally · cage
├─ scoreboard/{Dockerfile,app.py}
├─ scripts/solve.py          # the 5 reference exploits (stdlib, in-network)
├─ scripts/verify.sh         # self-check wrapper
└─ organizer/                # FLAGS · SOLUTION · DESIGN-NOTES
```

## Why it's hard (and fair)

Unlike a "spot the tell" range, these need real work: write the algebra (reverb,
echo), reverse the ISA gap (cage), realize keystream reuse and match the label
length (tally), or see the order-of-operations auth bug (warden). Each widget
hands you exactly the oracle its intended attack needs and nothing else — no brute
force, no fuzzing. Every flaw is fully determined and deterministically solvable;
the secrets are random per boot and the solver recovers or sidesteps them every
run, so `make reset && make check` stays green.

Full walkthrough with derivations: **[`organizer/SOLUTION.md`](organizer/SOLUTION.md)**.
Design rationale and originality notes: **[`organizer/DESIGN-NOTES.md`](organizer/DESIGN-NOTES.md)**.
