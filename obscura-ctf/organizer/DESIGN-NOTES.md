# Obscura — design notes

## Brief

Build a range of **original** vulnerabilities — invented from first principles,
not traceable to any CVE, public PoC, or KEV entry — and make them **genuinely
hard**: not "recognize the textbook tell" (that's Bastion) but "derive the
attack." Each widget should look sound, use real primitives correctly *except for
one deliberate design decision*, and fall to a short, exact exploit once that
decision is understood.

## Why these five, and why they're original

None of these is a known advisory. Each is a *new instance* built around a
principle, chosen so the flaw is invisible black-box and the fix is a one-liner:

| Widget | Principle exploited | Original twist |
|--------|--------------------|----------------|
| reverb | nonce relations break DSA/Schnorr | nonce = **public geometric sequence** `seed·r^i`; break is pure 2×2 linear algebra, no lattice |
| echo   | Fiat–Shamir soundness needs commitment binding | challenge hashes `Y‖nonce` but **not** `t`; attacker forges from public key alone |
| warden | canonicalize-then-authorize ordering | prefix check **and HMAC** both run on the raw, pre-decode path; decode/normalize deferred to fetch |
| tally  | keystream/nonce reuse | KDF keys on **`len(label)`** only, silently aliasing every same-length label |
| cage   | verifier must match runtime semantics | verifier checks jump **bounds** but not **alignment**; overlapping-instruction jump into an immediate |

Spread across domains — signatures, zero-knowledge, web/auth, symmetric crypto,
and sandbox/RE — so the board doesn't repeat one skill.

## Distinct from the rest of the repo

Deliberately avoids overlap with the existing ranges:

- **Not** the HNP biased-nonce lattice (keyhaven) — reverb is a *linear* nonce
  relation solved with a 2×2 system, a different mechanism and a different math.
- **Not** ECDSA nonce reuse (gauntlet) — reverb's nonces are all distinct; the
  break comes from their algebraic *dependence*, not a repeat.
- **Not** the CBC padding oracle (keyhaven) or GCM forbidden attack (deepend) —
  tally is keystream reuse via a KDF aliasing bug.
- **Not** a known CVE board (backlog) — every flaw here is invented; there is no
  advisory, product, or write-up behind any of them.
- echo (Fiat–Shamir without commitment binding) and cage (verifier/VM
  overlapping-instruction mismatch) are new to the collection entirely.

## Difficulty philosophy

- **Brutal black-box, trivial once seen.** Each widget hands you exactly the oracle
  the intended attack needs (a signing oracle, a challenge endpoint, a sealing
  oracle, a run endpoint) and nothing extra. No brute force, no fuzzing, no recon
  rabbit holes.
- **Derivation, not recognition.** reverb and echo need you to actually write the
  algebra; cage needs you to reverse the ISA gap; tally needs the keystream-reuse
  realization *and* the length-matching step; warden needs the order-of-operations
  insight. The hints in `challenge/BRIEF.md` nudge toward the shape without
  handing over the exploit.
- **Fair.** Every flaw is fully determined and deterministically solvable; the
  reference solver recovers or sidesteps the fresh random secrets every boot.

## Implementation

- One shared `python:3.12-slim` + Flask image (`app/`), dispatched by `$CHALLENGE`
  to `challenges/cN_*.py`, mirroring `backlog-ctf`. Scoreboard is a sixth tiny
  service. Pure stdlib crypto/VM — no `cryptography`, no `pycryptodome`.
- Crypto group lives in `app/common.py` (RFC 3526 2048-bit safe prime, `g=4`,
  exponents mod `q=(p−1)/2`). No EC, no parameter generation at boot.
- Secrets are random per boot (`os.urandom`, `secrets.randbelow`), so flags can't
  be precomputed and the self-check genuinely re-solves each run.

## Hardening against unintended solves

- reverb refuses to sign `grant-admin` and only accepts a *verifying* signature on
  exactly that message — no shortcut but key recovery.
- echo requires a server-issued, single-use `nonce`; the only way to satisfy
  `g^z == t·Y^e` without `x` is the commitment back-solve.
- warden keeps a `startswith('/data')` guard after normalization, so the traversal
  crosses `public → admin` *inside* the data root but cannot escape to the host FS.
- tally reserves the literal label `admin`; same-length labels are the intended
  (and only) path to the shared keystream.
- cage rejects a literal `0x20` opcode and unknown opcodes; a hidden-but-unreached
  `0x20` verifies but emits nothing — only the misaligned jump reaches it.

## Known / accepted properties

- Flags are visible in the challenge source under `organizer`-adjacent paths (by
  design; this is a training artifact, consistent with the rest of the repo).
- `cage`'s ISA is published in the brief — it must be, since opcodes can't be
  guessed black-box; the *puzzle* is the verifier gap, not the instruction set.
