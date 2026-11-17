# Flags (organizer)

All 5 verified live via `scripts/solve.py` (RESULT: ALL 5 FLAGS CAPTURED, exit 0).

| # | Port | Widget | Flag | One-line exploit |
|---|------|--------|------|------------------|
| 1 | 8601 | reverb | `FLAG{reverb_deterministic_nonces_are_linear_8f3c91}` | two signatures → solve `s_i = seed·r^i + e_i·d` for `d` → forge Schnorr sig on `grant-admin` |
| 2 | 8602 | echo   | `FLAG{echo_fiat_shamir_must_bind_the_commitment_a7d20e}` | `e=H(Y‖nonce)`; pick `z`, set `t = g^z·Y^(−e)`; POST `/login` — accepts with no witness |
| 3 | 8603 | warden | `FLAG{warden_authorize_then_normalize_is_backwards_5b1e74}` | token for `/public/%2e%2e/admin/flag.txt` (starts with `/public/`), then fetch → decodes/normalizes to `/admin/flag.txt` |
| 4 | 8604 | tally  | `FLAG{tally_keystream_keyed_only_by_label_length_d48a06}` | seal `00…` (len = admin ct) under any 5-char label → that's the keystream → XOR admin ct |
| 5 | 8605 | cage   | `FLAG{cage_verifier_scans_linearly_the_vm_jumps_anywhere_c0ffee}` | program `01 20 10 01` = `PUSH 0x20 ; JMP 1`; VM lands on `0x20` and runs `READFLAG` |

## Where the flags live

- **reverb / echo / tally / cage** — embedded as `FLAG = ...` in the module
  (`app/challenges/cN_*.py`). The shared image also writes `/flag` at boot, which
  nothing here reads (kept for parity with the other ranges).
- **warden** — written to `/data/admin/flag.txt` inside the container at startup;
  `/data/public/manual.txt` is the only file a legitimate token can reach.

## Scoring suggestion

These are not "recognize the tell" one-liners like Bastion — each needs a correct
derivation. Suggested flat weights by how much math/RE is required:

| Widget | Why | Points |
|--------|-----|--------|
| warden | order-of-operations auth bug; pure web, no math | **200** |
| tally  | spot keystream reuse, match label length | **250** |
| cage   | reverse the ISA gap, craft overlapping instruction | **300** |
| reverb | set up & solve a 2×2 linear system mod q, then forge | **350** |
| echo   | understand Fiat-Shamir soundness; forge without the witness | **350** |

A strong solo player clears the board in an afternoon; each widget stands alone
for teaching one idea.

## Notes

- `make check` runs every exploit from a throwaway `python:3.12-slim` container on
  `obscura_net`, reaching widgets by service name (`c1`..`c5`). Pure stdlib.
- Secrets (`_d`, `_x`, `_seed`, master key, HMAC key) are freshly random per boot;
  the exploits recover or sidestep them every time, so `make reset && make check`
  stays green with different keys.
