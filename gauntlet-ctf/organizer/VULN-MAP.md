# The Gauntlet — vulnerability map (ORGANIZER)

Seven independent challenges, each a faithful **minimal** model of a research-grade
EVM/crypto primitive. The omitted safeguard is called out in a comment in every
source file.

| # | Challenge | Class | Source |
|---|-----------|-------|--------|
| 1 | The Signet | ECDSA nonce reuse (key recovery) | [src/C1Signet.sol](../contracts/src/C1Signet.sol) |
| 2 | The Branch | Merkle second-preimage | [src/C2Branch.sol](../contracts/src/C2Branch.sol) |
| 3 | The Phantom | ecrecover == address(0) | [src/C3Phantom.sol](../contracts/src/C3Phantom.sol) |
| 4 | The Latch | EIP-1153 transient-storage reentrancy | [src/C4Latch.sol](../contracts/src/C4Latch.sol) |
| 5 | The Dice | Weak randomness (prevrandao) | [src/C5Dice.sol](../contracts/src/C5Dice.sol) |
| 6 | The Clash | Selector/facet delegatecall hijack | [src/C6Clash.sol](../contracts/src/C6Clash.sol) |
| 7 | The Keystone | BN254 pairing-verifier bypass | [src/C7Keystone.sol](../contracts/src/C7Keystone.sol) |

## Mechanisms

### 1 — ECDSA nonce reuse
The vault stores two past signatures by its authorizer that reuse the nonce `k`
(so both share `r`). From `s1 = k⁻¹(h1 + r·d)` and `s2 = k⁻¹(h2 + r·d)`:
`k = (h1−h2)/(s1−s2)` and `d = (s1·k − h1)/r` (mod n). The solver computes `d`
on-chain with `mulmod`/`addmod` and the modexp precompile, signs the withdraw
digest, and drains. *Fix:* never reuse a nonce (RFC-6979 deterministic `k`).

### 2 — Merkle second-preimage
Leaves are `keccak256(a, b)` — a 64-byte preimage, identical in shape to an
internal node `keccak256(left, right)`. So any internal node value can be re-sold
as a "leaf": the attacker submits `(a,b) = (leaf0, leaf1)`, whose hash equals the
real node `P01`, with proof `[P23]`. The payout `uint256(b)` is a child hash —
astronomically large — so one claim empties the airdrop. *Fix:* domain-separate
leaves from nodes (e.g. double-hash leaves, or a 1-byte prefix).

### 3 — ecrecover == address(0)
`ecrecover` returns `address(0)` on a malformed signature, and the vault's
`recoveryGuardian` was never initialized (also `address(0)`). A junk signature
(`r=s=0`) therefore satisfies `ecrecover(...) == recoveryGuardian`. *Fix:*
reject `ecrecover == address(0)` and never compare against an unset signer.

### 4 — EIP-1153 transient-storage reentrancy
The reentrancy guard uses `tstore`/`tload` (Cancun) but keys the lock by
`msg.sig`, so each function gets its own lock. `withdraw()` and
`emergencyWithdraw()` pay the same balance; re-entering the *other* from the ETH
callback isn't blocked, so the balance is paid twice (cross-function
reentrancy). *Fix:* a single global lock slot, not per-selector; update state
before the external call.

### 5 — Weak randomness
The roll is `uint256(keccak256(block.prevrandao)) % 6 + 1`. `prevrandao` is fixed
within a block and readable by any contract, so the attacker recomputes the roll
and bets it in the same transaction. *Fix:* a commit-reveal scheme or an external
randomness beacon (VRF).

### 6 — Selector/facet delegatecall hijack
The diamond-style router `delegatecall`s `facets[msg.sig]`, but `setFacet` has no
access control. The attacker registers a facet that forwards
`address(this).balance` (the router's, under delegatecall) to the caller, then
invokes it through the router. *Fix:* restrict facet registration to the owner /
a governance process.

### 7 — BN254 pairing-verifier bypass
The verifier checks only `e(A, VK) · e(C, VK) == 1` and never binds `A, C` to a
public statement or checks they are non-trivial subgroup elements. By bilinearity
the equation holds for any `A` with `C = −A` (and for `A = C = O`), so a valid
"proof" is forged from the generator with no witness. The solver submits
`A = (1,2)`, `C = (1, q−2)`. *Fix:* a complete Groth16 check that binds the proof
to the verifying key and public inputs, plus subgroup/zero checks.

## Accounts & chain

- One `anvil` chain pinned to **Cancun** (for EIP-1153 and the BN254
  precompiles), chain-id 31337; account[0] deploys, account[1] attacks (public
  anvil keys).
- Each `Setup.isSolved()` encodes the win condition (see [FLAGS.md](FLAGS.md));
  the dispenser reads it on-chain before releasing a flag.
