# Reentrant

> A DeFi protocol, thoroughly **rekt**.

**Reentrant** is a smart-contract CTF: six **independent** on-chain challenges,
each a different deep, famous DeFi vulnerability class. They run on a local
`anvil` chain; each flag `RKT{...}` is released by the dispenser **only when the
challenge is actually solved on-chain** (it checks the challenge's `isSolved()`
via `eth_call` — you can't guess your way in).

| # | Challenge | Vulnerability class (the mental model) | Real-world echo |
|---|-----------|----------------------------------------|-----------------|
| 1 | **The Vault** | **Reentrancy** — ETH sent before the balance is zeroed; re-enter and drain | The DAO (2016) |
| 2 | **The Oracle** | **Spot-price oracle manipulation** — crash a tiny AMM's price, then borrow the lending pool dry | bZx / Harvest / Mango |
| 3 | **The Admin** | **Unprotected initializer** — re-initialize to become owner, then sweep | Parity init, Rubixi |
| 4 | **The Permit** | **Signature replay** — a voucher with no nonce/deadline, replayed until drained | permit / meta-tx replays |
| 5 | **The Upgrade** | **Proxy storage collision** — a delegatecall whose slot write overwrites the proxy's owner | Parity multisig (2017) |
| 6 | **The Shares** | **ERC-4626 first-depositor inflation** — donate to inflate share price, round the victim to 0 shares, redeem it all | ERC-4626 inflation attacks |

Each target is a faithful **minimal** re-implementation of its vulnerability
class (not a copy of any specific audited protocol). The docs note the real hack
each one echoes; none claims to reproduce that exact incident.

## Run it

```bash
make up        # build the chain, deploy all 6 challenges, start the scoreboard
make check     # run every exploit in-network and prove all 6 flags, exit 0
make down      # stop + remove everything
```

- **Scoreboard:** http://localhost:8502 — live `isSolved()` status for each challenge
- **Chain RPC:** http://localhost:8545 — chain-id `31337`, standard anvil accounts

Ports are overridable: `RPC_PORT=9545 SB_PORT=9502 make up`.

## How you play

Everything is driven **on-chain**. The attacker is `anvil` account[1]
(key `0x59c6…690d`); the protocol was deployed by account[0]. Point `cast` /
`forge` at the RPC, read each challenge's `Setup` contract (its address is on the
scoreboard) to find the target, and exploit it. When your exploit makes
`Setup.isSolved()` return true, the scoreboard reveals that flag.

See [challenge/BRIEF.md](challenge/BRIEF.md) for the player brief and hints.

## Architecture

- `services/chain` — the `anvil` dev chain.
- `contracts/` — a self-contained Foundry project (no forge-std; a tiny vendored
  cheatcode shim). `src/C1…C6` are the challenges; `script/Deploy.s.sol` seeds
  them; `script/solve/*` are the reference exploits; `scripts/verify.sh` runs them.
- `services/dispenser` — the scoreboard and the **flag oracle**: it holds the
  flags and verifies `isSolved()` on-chain before releasing each one.

## Organizer

- [organizer/VULN-MAP.md](organizer/VULN-MAP.md) — each bug, its mechanism, and the faithful re-impl
- [organizer/FLAGS.md](organizer/FLAGS.md) — the flag sheet
- [organizer/SOLUTION.md](organizer/SOLUTION.md) — the full exploit walkthrough
- [organizer/DESIGN-NOTES.md](organizer/DESIGN-NOTES.md) — why it's built this way

> ⚠️ Every contract here is a deliberately vulnerable teaching artifact. Do not
> deploy any of it to a real network.
