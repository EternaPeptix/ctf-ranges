# Delphi — flag sheet (ORGANIZER ONLY)

| # | Challenge | Oracle flaw | Flag |
|---|-----------|-------------|------|
| 1 | The Floor | Chainlink `minAnswer` clamp | `ORC{m1n4nsw3r_cl4mp_lun4_fl00r_pr1c3_r3ad}` |
| 2 | The Stale | Missing freshness check | `ORC{st4l3_f33d_n0_fr3shn3ss_ch3ck_h34rtb34t}` |
| 3 | The Window | Short-window TWAP manipulation | `ORC{tw4p_sh0rt_w1nd0w_t1m3_w31ght3d_m4n1p}` |
| 4 | The Mirror | Read-only reentrancy on LP price | `ORC{r34d_0nly_r33ntr4ncy_v1rtu4l_pr1c3}` |
| 5 | The Mint | Naive LP-token spot pricing | `ORC{n41v3_lp_t0k3n_sp0t_r3s3rv3_pr1c1ng}` |
| 6 | The Scale | Oracle decimals / scaling confusion | `ORC{0r4cl3_d3c1m4ls_sc4l1ng_c0nfus10n_1e10}` |

## Win condition per challenge (`Setup.isSolved()`)

| # | isSolved() true when |
|---|----------------------|
| 1 | `usdx.balanceOf(lending) == 0` (lending pool drained) |
| 2 | `usdx.balanceOf(vault) == 0` (reserves drained at the stale price) |
| 3 | `usdx.balanceOf(lending) == 0` (borrowed against the pumped TWAP) |
| 4 | `address(desk).balance == 0` (desk drained during the reentrant window) |
| 5 | `usdx.balanceOf(desk) == 0` (desk drained against the inflated LP price) |
| 6 | `usdx.balanceOf(lending) == 0` (1e10 mis-scaling) |

## How flags are released

The dispenser holds the flag strings (they are **not** in the contract
bytecode). For each challenge it calls `isSolved()` via `eth_call` (selector
`0x64d98f6e`) and returns the flag only when it reads `true`.

Self-check: `make check` runs [../scripts/verify.sh](../scripts/verify.sh)
(exploits + on-chain verification) → **ALL 6 FLAGS CAPTURED, exit 0**. Challenge 3
advances the chain clock (`evm_increaseTime`) between its manipulation and drain.
