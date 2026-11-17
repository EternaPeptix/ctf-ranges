# Reentrant — player brief

A DeFi startup shipped fast and audited never. Six of its contracts are live on
a local chain. Drain them.

## Setup

- **Chain:** `http://localhost:8545`, chain-id `31337`.
- **You** are `anvil` account[1]: `0x70997970C51812dc3A010C7d01b50e0d17dc79C8`,
  key `0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d`
  (10000 ETH to play with; some challenges also pre-fund you with tokens).
- **Scoreboard:** `http://localhost:8502` — lists each challenge's `Setup`
  contract and shows `isSolved()` live.

Each challenge is a `Setup` contract exposing `isSolved()` and getters for the
target(s) it deployed. Solve = make `isSolved()` return true; the scoreboard
then reveals the flag. Tooling: `cast`, `forge script`, or anything that speaks
JSON-RPC.

```bash
# e.g. read a target out of its Setup, then poke it
cast call <SETUP> "vault()(address)" --rpc-url http://localhost:8545
```

## The six

1. **The Vault** — a pooled ETH vault. Deposit, withdraw… look very closely at
   the *order* of operations in `withdraw()`.
2. **The Oracle** — a lending pool that prices token collateral off a tiny AMM's
   current reserves. What stops you from moving that price yourself first?
3. **The Admin** — a treasury with an owner-only `sweep()`. How did it decide
   who the owner is, and can you decide again?
4. **The Permit** — pays out against a signed voucher. You have one valid
   voucher for 1 ETH. The pot is bigger than 1 ETH…
5. **The Upgrade** — a proxy wallet that `delegatecall`s a logic contract. Line
   up their storage slots.
6. **The Shares** — an ERC-4626-style vault. Be the **first** depositor, then
   make the next one's deposit worth nothing.

## Hints

<details><summary>1 — Reentrancy</summary>
`withdraw()` sends ETH before it zeroes your balance. Deploy a contract whose
<code>receive()</code> calls <code>withdraw()</code> again while the vault still
has funds.</details>

<details><summary>2 — Oracle</summary>
Collateral value = AMM reserve ratio. You're seeded with lots of tokens; dump
them into the AMM to crash the token's price, then borrow all 100 pool tokens
for almost no ETH.</details>

<details><summary>3 — Admin</summary>
<code>initialize()</code> has no "already initialized" guard. Call it with your
own address, then <code>sweep()</code>.</details>

<details><summary>4 — Permit</summary>
The signed digest is just <code>keccak(to, amount)</code> — no nonce, nothing
marks it used. Call <code>claim()</code> with the same voucher until the pot is
empty.</details>

<details><summary>5 — Upgrade</summary>
Proxy slot 1 is <code>owner</code>; the logic contract's slot 1 is a field a
public function sets. Call that function through the proxy to overwrite
<code>owner</code>, then <code>sweep()</code>.</details>

<details><summary>6 — Shares</summary>
Deposit 1 wei (1 share), transfer a big donation straight to the vault to spike
the share price, let the victim deposit (rounds to 0 shares), then redeem your 1
share for everything.</details>
