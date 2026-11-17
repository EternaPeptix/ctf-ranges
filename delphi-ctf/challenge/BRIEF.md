# Delphi — player brief

Six DeFi protocols, each trusting a price it shouldn't. Break the price, drain
the protocol.

## Setup

- **Chain:** `http://localhost:8547`, chain-id `31337`.
- **You** are `anvil` account[1]: `0x70997970C51812dc3A010C7d01b50e0d17dc79C8`,
  key `0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d`.
  Several challenges pre-fund you with the tokens/capital you need.
- **Scoreboard:** `http://localhost:8503` — each challenge's `Setup` address +
  live `isSolved()`.

Each `Setup` exposes `isSolved()` and getters for the contracts it deployed.
Solve = make `isSolved()` true; the scoreboard then reveals the flag. Use `cast`
/ `forge script`.

```bash
cast call <SETUP> "lending()(address)" --rpc-url http://localhost:8547
```

## The six

1. **The Floor** — a lending market on a token whose feed has a `minAnswer`. The
   token has crashed. What does the feed report now, and what is the token
   really worth?
2. **The Stale** — a vault that buys the token at the oracle price. When was that
   price last updated?
3. **The Window** — collateral is valued by a TWAP. The window is short. You can
   move the spot price, and you can make time pass.
4. **The Mirror** — a desk lends against an LP token valued at its "virtual
   price". What is that price *during* a `removeLiquidity` call, before the pool
   finishes settling?
5. **The Mint** — an LP token priced off the pool's spot reserves. There's a
   flash lender next door.
6. **The Scale** — a lending market whose price feed isn't the usual 8 decimals.

## Hints

<details><summary>1 — Floor</summary>
The real price is below <code>minAnswer</code>, so <code>latestAnswer()</code>
returns the $1 floor. You were handed a pile of the crashed token — deposit it
at the floored price and borrow the pool dry.</details>

<details><summary>2 — Stale</summary>
<code>sellToken()</code> never checks <code>updatedAt</code>. The feed is frozen
at $100; your tokens are really worth ~0. Sell them all into the vault.</details>

<details><summary>3 — Window</summary>
Pump the pool (<code>buyToken</code>), call <code>oracle.update()</code> to set a
checkpoint, advance the clock past <code>PERIOD</code> (600s) with
<code>cast rpc evm_increaseTime 700</code> + <code>evm_mine</code>, call
<code>update()</code> again — now the TWAP is the pumped price — then deposit and
borrow.</details>

<details><summary>4 — Mirror</summary>
<code>removeLiquidity</code> burns your LP and sends ETH <em>before</em> sending
the token side, so <code>getVirtualPrice()</code> spikes during the ETH
callback. Deposit a little LP as collateral, then remove the rest from an
attacker contract whose <code>receive()</code> borrows the desk dry.</details>

<details><summary>5 — Mint</summary>
LP price = (reserveToken + reserveUSDX)/supply, spot. Flash-borrow USDX, swap it
in to imbalance the pool (the sum balloons), borrow against your LP collateral,
swap back, repay.</details>

<details><summary>6 — Scale</summary>
The feed is 18 decimals but the code divides by <code>1e8</code>. One $1 token is
valued at $10¹⁰. Deposit 1 and borrow everything.</details>
