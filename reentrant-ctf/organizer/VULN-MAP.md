# Reentrant — vulnerability map (ORGANIZER)

Six independent challenges, each a faithful **minimal** re-implementation of a
distinct, well-known DeFi vulnerability *class*. These are teaching models of the
bug mechanics, not copies of any specific audited protocol; the "echo" column is
the famous real-world incident the class is associated with.

| # | Challenge | Class | Echo | Source |
|---|-----------|-------|------|--------|
| 1 | The Vault | Reentrancy (CEI violation) | The DAO (2016) | [src/C1Vault.sol](../contracts/src/C1Vault.sol) |
| 2 | The Oracle | Spot-price oracle manipulation | bZx / Harvest / Mango | [src/C2Oracle.sol](../contracts/src/C2Oracle.sol) |
| 3 | The Admin | Unprotected initializer / broken access control | Parity init, Rubixi | [src/C3Admin.sol](../contracts/src/C3Admin.sol) |
| 4 | The Permit | Signature replay | permit / meta-tx replays | [src/C4Permit.sol](../contracts/src/C4Permit.sol) |
| 5 | The Upgrade | Proxy storage collision via delegatecall | Parity multisig (2017) | [src/C5Upgrade.sol](../contracts/src/C5Upgrade.sol) |
| 6 | The Shares | ERC-4626 first-depositor share inflation | ERC-4626 inflation | [src/C6Shares.sol](../contracts/src/C6Shares.sol) |

## Mechanisms

### 1 — Reentrancy
`Vault.withdraw()` performs the external ETH transfer **before** zeroing the
caller's balance (Checks-Effects-Interactions, violated). A malicious receiver
re-enters `withdraw()` while its recorded balance is still non-zero and drains
the pooled funds. *Fix:* zero the balance before the call, or a reentrancy guard.

### 2 — Spot-price oracle manipulation
`LendingPool.borrow()` values token collateral at `AMM.priceTokenInEth()`, the
*instantaneous* reserve ratio of a small on-chain pool. The attacker is seeded
with enough tokens to dominate the AMM; selling them crashes the token's spot
price, so the required ETH collateral for borrowing the pool's 100 tokens
collapses to dust. *Fix:* a manipulation-resistant oracle (TWAP / off-chain
feed), not a spot ratio.

### 3 — Unprotected initializer
`Treasury.initialize()` sets `owner` with no "already initialized" guard, so it
can be called again by anyone. The attacker re-initializes to themselves and
calls the owner-only `sweep()`. *Fix:* an `initializer` modifier / one-shot guard.

### 4 — Signature replay
`Payments.claim()` verifies `ecrecover` over `keccak256(to, amount)` — no nonce,
no deadline, no used-voucher marker. One legitimately-signed voucher (for the
attacker, 1 ETH) can be replayed until the pot is empty. *Fix:* bind a nonce +
deadline (+ chain-id/contract) into the digest and record consumed vouchers.

### 5 — Proxy storage collision
`WalletProxy` lays out `implementation` (slot 0) and `owner` (slot 1).
`WalletLogic` lays out `pending` (slot 0) and `nominee` (slot 1). Calling
`nominate()` **through the proxy** (delegatecall) writes `nominee` into the
proxy's slot 1 — i.e. `owner` — so the attacker becomes owner and sweeps. *Fix:*
EIP-1967 unstructured storage so proxy and logic slots never collide.

### 6 — ERC-4626 first-depositor inflation
`Vault4626.deposit()` prices shares off the raw asset balance with no virtual
offset. The attacker mints 1 share for 1 wei, **donates** a large amount directly
to the vault to inflate the share price, and the victim's subsequent deposit
rounds down to **0 shares** while their assets enter the vault. The attacker then
redeems their single share for the whole balance. *Fix:* virtual shares/assets
(OpenZeppelin's `_decimalsOffset`) or a dead-shares mint on first deposit.

## Faithfulness & accounts

- One `anvil` chain (chain-id 31337), standard accounts: account[0] deploys the
  protocol; account[1] is the attacker. Keys are the public anvil defaults.
- The C4 voucher is signed by an **organizer-only** key (constant in
  [Deploy.s.sol](../contracts/script/Deploy.s.sol)); the attacker only ever gets
  the signature, never the key — the vuln is the replay, not key disclosure.
- Each `Setup.isSolved()` encodes the win condition (see [FLAGS.md](FLAGS.md));
  the dispenser reads it on-chain before releasing a flag.
