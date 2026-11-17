# The Gauntlet

> The hardest range. An ultimate test.

**The Gauntlet** is seven **independent** on-chain challenges, each a
research-grade EVM or cryptographic primitive — the kind of bug that stumps
experienced auditors. They run on a local `anvil` chain (pinned to **Cancun**);
each flag `GG{...}` is released by the dispenser **only when the challenge is
actually solved on-chain** (it checks `isSolved()` via `eth_call`).

| # | Challenge | Technique | Why it's brutal |
|---|-----------|-----------|-----------------|
| 1 | **The Signet** | **ECDSA nonce reuse** → private-key recovery | two leaked signatures share `k`; recover `d` with modular arithmetic and forge the admin signature |
| 2 | **The Branch** | **Merkle second-preimage** (leaf/node confusion) | 64-byte leaves have the same preimage shape as internal nodes — pass a node off as a leaf to forge a payout |
| 3 | **The Phantom** | **`ecrecover` returns `address(0)`** | an uninitialized guardian is `address(0)`; a malformed signature recovers to `address(0)` and authorizes you |
| 4 | **The Latch** | **EIP-1153 transient-storage reentrancy** | a modern `tstore`/`tload` lock keyed per-selector — bypassed by cross-function reentrancy (Cancun-era) |
| 5 | **The Dice** | **Weak randomness** (`prevrandao`) | a "provably fair" roll you recompute in the same block and bet |
| 6 | **The Clash** | **Selector/facet delegatecall hijack** | a diamond router with unprotected facet registration — run your code in the router's context and drain it |
| 7 | **The Keystone** | **BN254 pairing-verifier bypass** *(capstone)* | a Groth16-style verifier missing a soundness check — forge a "proof" from the generator with the `ecPairing` precompile |

Each target is a faithful **minimal** model of its primitive, with the omitted
safeguard called out in a comment.

## Run it

```bash
make up        # build the Cancun chain, deploy all 7 challenges, start the board
make check     # run every exploit in-network and prove all 7 flags, exit 0
make down      # stop + remove everything
```

- **Scoreboard:** http://localhost:8504 — live `isSolved()` status per challenge
- **Chain RPC:** http://localhost:8549 — chain-id `31337`, Cancun, standard anvil accounts

Ports are overridable: `RPC_PORT=9549 SB_PORT=9504 make up`.

## How you play

Everything is driven **on-chain**. The attacker is `anvil` account[1]
(key `0x59c6…690d`). Point `cast` / `forge` at the RPC, read each challenge's
`Setup` (address on the scoreboard) to find the target, and exploit. When your
exploit makes `Setup.isSolved()` true, the scoreboard reveals the flag.

See [challenge/BRIEF.md](challenge/BRIEF.md) for hints.

## Organizer

- [organizer/VULN-MAP.md](organizer/VULN-MAP.md) — each primitive, its mechanism, and the faithful re-impl
- [organizer/FLAGS.md](organizer/FLAGS.md) — the flag sheet
- [organizer/SOLUTION.md](organizer/SOLUTION.md) — the full exploit walkthrough
- [organizer/DESIGN-NOTES.md](organizer/DESIGN-NOTES.md) — why it's built this way

> ⚠️ Every contract here is a deliberately vulnerable teaching artifact. Do not
> deploy any of it to a real network.
