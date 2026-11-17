# The Gauntlet — player brief

Seven fortified contracts. Each guards a prize behind one hard primitive. Pick
every lock.

## Setup

- **Chain:** `http://localhost:8549`, chain-id `31337` (Cancun).
- **You** are `anvil` account[1]: `0x70997970C51812dc3A010C7d01b50e0d17dc79C8`,
  key `0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d`.
- **Scoreboard:** `http://localhost:8504` — each `Setup` address + live `isSolved()`.

Solve = make `isSolved()` true; the scoreboard reveals the flag. Use `cast` /
`forge script`.

## The seven

1. **The Signet** — the vault's authorizer leaked two signatures. Look closely
   at their `r` values.
2. **The Branch** — an airdrop Merkle verifier. The leaves are two 32-byte
   fields. What else hashes two 32-byte fields the same way?
3. **The Phantom** — an emergency withdrawal gated by a signature check against a
   guardian that was never set.
4. **The Latch** — a bank with a shiny transient-storage reentrancy guard. What
   is the lock keyed on?
5. **The Dice** — a dice game seeded by on-chain "randomness".
6. **The Clash** — a diamond router that `delegatecall`s per-selector facets. Who
   is allowed to register a facet?
7. **The Keystone** — a pairing-based proof verifier. What does it actually
   constrain about the proof?

## Hints

<details><summary>1 — Signet</summary>
Same `r` ⇒ reused nonce `k`. From (r,s1,h1),(r,s2,h2):
<code>k=(h1-h2)/(s1-s2)</code>, <code>d=(s1·k-h1)/r</code> mod n. Then sign the
<code>WITHDRAW_DIGEST</code> with <code>d</code>.</details>

<details><summary>2 — Branch</summary>
<code>leaf = keccak256(a,b)</code> is a 64-byte preimage — identical to an internal
node <code>keccak256(left,right)</code>. Read <code>leaves()</code>, take two of
them (l0,l1) as (a,b): <code>keccak(l0,l1)</code> is the real node P01. Give proof
<code>[keccak(l2,l3)]</code>. Payout is <code>uint256(l1)</code> — a hash, i.e.
enormous.</details>

<details><summary>3 — Phantom</summary>
<code>recoveryGuardian == address(0)</code>, and <code>ecrecover</code> returns
<code>address(0)</code> for a bad signature. Call with <code>v=27, r=0, s=0</code>.</details>

<details><summary>4 — Latch</summary>
The lock is keyed by <code>msg.sig</code> — per function. <code>withdraw()</code>
and <code>emergencyWithdraw()</code> pay the same balance under different locks.
Deposit, call withdraw, and re-enter emergencyWithdraw from the callback.</details>

<details><summary>5 — Dice</summary>
The roll is <code>uint256(keccak256(block.prevrandao)) % 6 + 1</code>. Compute it
in your own contract and call <code>roll()</code> with the answer in the same
transaction (and add a <code>receive()</code> to collect).</details>

<details><summary>6 — Clash</summary>
<code>setFacet</code> has no access control. Deploy a facet that sends
<code>address(this).balance</code> to <code>msg.sender</code>, register it for its
selector, and call it through the router (delegatecall ⇒ <code>address(this)</code>
is the router).</details>

<details><summary>7 — Keystone</summary>
The verifier only checks <code>e(A,VK)·e(C,VK)==1</code>. By bilinearity that holds
for <code>C = -A</code>. Submit <code>A=(1,2)</code> (G1 generator),
<code>C=(1, q-2)</code>.</details>
