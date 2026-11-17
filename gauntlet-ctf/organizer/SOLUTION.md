# The Gauntlet — full solution (ORGANIZER)

All seven are solved on-chain against `http://localhost:8549` as the attacker
(anvil account[1]). The reference exploits are the Foundry scripts in
[../contracts/script/solve/](../contracts/script/solve/); `make check` runs them
all and then asks the dispenser for each flag (verifying `isSolved()` on-chain).

```bash
export RPC=http://localhost:8549
export PK=0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d
SETUP=<addr> forge script script/solve/SolveC1.s.sol:SolveC1 --rpc-url $RPC --private-key $PK --broadcast
```

Setup addresses: scoreboard `GET /` or `GET /challenges`.

---

## 1 — The Signet (ECDSA nonce reuse)
Read `R, S1, H1, S2, H2` off the vault. With `n` = secp256k1 order:
`k = (H1−H2)/(S1−S2)`, `d = (S1·k − H1)/R` (mod n). Sign `WITHDRAW_DIGEST` with
`d` (`vm.sign`) and call `withdraw(you, v, r, s)`. See
[SolveC1.s.sol](../contracts/script/solve/SolveC1.s.sol). Flag
`GG{3cdsa_n0nc3_r3us3_pr1v4t3_k3y_r3c0v3ry}`.

## 2 — The Branch (Merkle second-preimage)
`l = vault.leaves()`. Submit `claim(l[0], l[1], [keccak256(l[2],l[3])])`: the
"leaf" `keccak256(l0,l1)` equals node `P01`, the proof reaches the root, and the
payout `uint256(l1)` drains the pot. Flag
`GG{m3rkl3_s3c0nd_pr31m4g3_l34f_n0d3_c0nfus10n}`.

## 3 — The Phantom (ecrecover==0)
`emergencyWithdraw(you, 27, bytes32(0), bytes32(0))` → `ecrecover` returns
`address(0)` == the unset guardian → drain. Flag
`GG{3cr3c0v3r_r3turns_z3r0_f0r_1nv4l1d_s1g}`.

## 4 — The Latch (transient-storage cross-function reentrancy)
Attacker contract: `deposit{value:100e18}` then `withdraw()`; its `receive()`
re-enters `emergencyWithdraw()` once (different selector ⇒ different transient
lock) → paid 100 twice → bank drained. See
[SolveC4.s.sol](../contracts/script/solve/SolveC4.s.sol). Flag
`GG{31p1153_tr4ns13nt_cr0ss_funct10n_r33ntr4ncy}`.

## 5 — The Dice (weak randomness)
Attacker contract computes `uint256(keccak256(block.prevrandao)) % 6 + 1` and
calls `roll(that)` in the same tx (with a `receive()` to collect). Flag
`GG{pr3vr4nd40_w34k_r4nd0mn3ss_s4m3_bl0ck}`.

## 6 — The Clash (facet hijack)
Deploy a facet whose `pwn()` sends `address(this).balance` to `msg.sender`;
`router.setFacet(pwn.selector, facet)`; call `pwn()` through the router. Under
delegatecall `address(this)` is the router, so its ETH goes to you. See
[SolveC6.s.sol](../contracts/script/solve/SolveC6.s.sol). Flag
`GG{s3l3ct0r_f4c3t_h1j4ck_d3l3g4t3c4ll_r0ut3r}`.

## 7 — The Keystone (pairing forgery)
The verifier checks only `e(A,VK)·e(C,VK)==1`. Submit `A = (1,2)` (G1 generator),
`C = (1, q−2)` (= −A); by bilinearity the product is 1, so the proof verifies and
the vault drains. `q` is the BN254 field modulus. See
[SolveC7.s.sol](../contracts/script/solve/SolveC7.s.sol). Flag
`GG{bn254_p41r1ng_v3r1f13r_z3r0_pr00f_f0rg3ry}`.

---

## One-shot

```bash
make up && make check     # -> ALL 7 FLAGS CAPTURED, exit 0
```
