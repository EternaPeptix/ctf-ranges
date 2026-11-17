# Delphi

> Every challenge is a different way that **trusting a price** goes wrong.

**Delphi** is an oracle-manipulation CTF: six **independent** on-chain challenges,
each a distinct, deep price-oracle flaw. They run on a local `anvil` chain; each
flag `ORC{...}` is released by the dispenser **only when the challenge is actually
solved on-chain** (it checks the challenge's `isSolved()` via `eth_call`).

| # | Challenge | Oracle flaw (the mental model) | Real-world echo |
|---|-----------|-------------------------------|-----------------|
| 1 | **The Floor** | **Chainlink `minAnswer` clamp** — the asset crashes to ~0 but the feed floors the price, so junk collateral still "borrows" | Venus / Blizz on LUNA |
| 2 | **The Stale** | **Missing freshness check** — a frozen feed is read without checking `updatedAt`; dump collapsed tokens at the stale high price | assorted staleness hacks |
| 3 | **The Window** | **Short-window TWAP** — pump spot, hold it for the averaging window, and the time-weighted average the market trusts drags up with it | Inverse Finance |
| 4 | **The Mirror** | **Read-only reentrancy** — re-enter mid-`removeLiquidity`, when the LP `virtualPrice` is transiently inflated, and borrow against the bogus mark | Curve read-only reentrancy |
| 5 | **The Mint** | **Naive LP-token pricing** — value an LP token off spot reserves; flash-loan to imbalance the pool and inflate your collateral | Warp Finance / Cheese Bank |
| 6 | **The Scale** | **Decimals / unit confusion** — mix an 18-decimal feed into code that assumes 8 decimals; a $1 token is valued at $10¹⁰ | oracle-integration bugs |

Each target is a faithful **minimal** re-implementation of its flaw (not a copy of
any specific protocol). "The market crashed" / "the feed froze" is simulated by
setting the mock feed's state, since a dev chain has no live market.

## Run it

```bash
make up        # build the chain, deploy all 6 challenges, start the scoreboard
make check     # run every exploit in-network and prove all 6 flags, exit 0
make down      # stop + remove everything
```

- **Scoreboard:** http://localhost:8503 — live `isSolved()` status per challenge
- **Chain RPC:** http://localhost:8547 — chain-id `31337`, standard anvil accounts

Ports are overridable: `RPC_PORT=9547 SB_PORT=9503 make up`.

## How you play

Everything is driven **on-chain**. The attacker is `anvil` account[1]
(key `0x59c6…690d`); the protocols were deployed by account[0]. Point `cast` /
`forge` at the RPC, read each challenge's `Setup` contract (address on the
scoreboard) to find the targets, and exploit. When your exploit makes
`Setup.isSolved()` return true, the scoreboard reveals that flag.

> Note: **The Window** (TWAP) requires advancing the chain clock past the
> averaging window — `cast rpc evm_increaseTime` / `evm_mine` between the
> manipulation and the drain. See the brief.

See [challenge/BRIEF.md](challenge/BRIEF.md) for hints.

## Organizer

- [organizer/VULN-MAP.md](organizer/VULN-MAP.md) — each oracle bug, its mechanism, and the faithful re-impl
- [organizer/FLAGS.md](organizer/FLAGS.md) — the flag sheet
- [organizer/SOLUTION.md](organizer/SOLUTION.md) — the full exploit walkthrough
- [organizer/DESIGN-NOTES.md](organizer/DESIGN-NOTES.md) — why it's built this way

> ⚠️ Every contract here is a deliberately vulnerable teaching artifact. Do not
> deploy any of it to a real network.
