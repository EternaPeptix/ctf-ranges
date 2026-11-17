# Delphi — vulnerability map (ORGANIZER)

Six independent challenges, each a faithful **minimal** model of a distinct
price-oracle flaw. These are teaching models of the mechanics, not copies of any
specific protocol; the "echo" is the famous incident the class is associated with.

| # | Challenge | Class | Echo | Source |
|---|-----------|-------|------|--------|
| 1 | The Floor | Chainlink `minAnswer` clamp | Venus / Blizz (LUNA) | [src/C1Floor.sol](../contracts/src/C1Floor.sol) |
| 2 | The Stale | Missing freshness check | assorted staleness hacks | [src/C2Stale.sol](../contracts/src/C2Stale.sol) |
| 3 | The Window | Short-window TWAP manipulation | Inverse Finance | [src/C3Window.sol](../contracts/src/C3Window.sol) |
| 4 | The Mirror | Read-only reentrancy on LP virtual price | Curve read-only reentrancy | [src/C4Mirror.sol](../contracts/src/C4Mirror.sol) |
| 5 | The Mint | Naive LP-token (spot reserve) pricing | Warp Finance / Cheese Bank | [src/C5Mint.sol](../contracts/src/C5Mint.sol) |
| 6 | The Scale | Oracle decimals / scaling confusion | integration bugs | [src/C6Scale.sol](../contracts/src/C6Scale.sol) |

Shared mocks (ERC20 + Chainlink-style aggregator): [src/common/Mocks.sol](../contracts/src/common/Mocks.sol).

## Mechanisms

### 1 — minAnswer clamp
`MockAggregator.latestAnswer()` clamps the reported price to `minAnswer`
(historically real on Chainlink feeds). The token's real price is set below the
$1 floor, so the feed keeps returning $1; `FloorLending` trusts it and lets the
attacker borrow against worthless collateral. *Fix:* reject prices at/near
`minAnswer`/`maxAnswer`.

### 2 — missing freshness check
`StaleVault.sellToken()` reads `latestRoundData()` but ignores `updatedAt`. The
Setup freezes the feed at $100 with an ancient timestamp while the token has
really collapsed; the attacker dumps the worthless tokens at the stale price.
*Fix:* `require(block.timestamp - updatedAt < heartbeat)`.

### 3 — short-window TWAP
`CumAMM` keeps a Uniswap-v2-style cumulative price; `TwapOracle` averages it over
a 600s `PERIOD`. The attacker pumps the pool, checkpoints, lets `PERIOD` elapse
(the price held the whole time), checkpoints again — the TWAP is now the pumped
price — and `WindowLending` over-values their collateral. *Fix:* a longer window
sized to the cost of holding a manipulated price, and multiple observations.

### 4 — read-only reentrancy
`StablePool.removeLiquidity()` decrements `totalLP` and sends ETH to the caller
**before** transferring the token side, so during the ETH callback
`getVirtualPrice()` is inflated (supply down, token reserve not yet paid out).
`LendingDesk.borrow()` reads the virtual price live, so an attacker contract that
re-enters `borrow()` from its `receive()` is credited the bogus value. *Fix:* a
reentrancy lock the read path also respects (Curve's `remove_liquidity` lock), or
update all balances before any external call.

### 5 — naive LP-token pricing
`LpDesk.lpPrice()` values the LP token as `(reserveToken + reserveUSDX)/totalLP`
— the spot reserves. Flash-borrowing USDX to imbalance the pool inflates that sum
(the constant-product curve moves value into the heavier side), so LP collateral
is over-valued; the attacker borrows, swaps back, and repays the flash loan.
*Fix:* fair LP pricing (Alpha Homora: `2·sqrt(r0·r1·p0·p1)/supply`).

### 6 — decimals / scaling confusion
`ScaleLending.borrow()` divides the feed answer by `1e8` (assuming an 8-decimal
Chainlink feed), but `MockAggregator` here reports **18** decimals, so every
valuation is inflated by `1e10`. A single $1 token is treated as $10¹⁰. *Fix:*
scale by the feed's actual `decimals()`.

## Accounts & simulation

- One `anvil` chain (chain-id 31337); account[0] deploys, account[1] attacks
  (public anvil keys). Challenges that need capital pre-fund the attacker.
- There is no live market on a dev chain, so "the price crashed / the feed froze"
  is simulated by the Setup calling `setAnswer` / `setAnswerStale` on the mock
  aggregator. The *bug* being taught is the protocol's trust in that value.
- Each `Setup.isSolved()` encodes the win condition (see [FLAGS.md](FLAGS.md));
  the dispenser reads it on-chain before releasing a flag.
