# Reentrant — flag sheet (ORGANIZER ONLY)

| # | Challenge | Vulnerability | Flag |
|---|-----------|---------------|------|
| 1 | The Vault | Reentrancy (CEI violation) | `RKT{r33ntr4ncy_c31_v10l4t10n_dr41n_th3_v4ult}` |
| 2 | The Oracle | Spot-price oracle manipulation | `RKT{sp0t_pr1c3_0r4cl3_fl4shl04n_m4n1pul4t10n}` |
| 3 | The Admin | Unprotected initializer / access control | `RKT{unpr0t3ct3d_1n1t_m1ss1ng_4cc3ss_c0ntr0l}` |
| 4 | The Permit | Signature replay (no nonce/deadline) | `RKT{s1gn4tur3_r3pl4y_n0_n0nc3_n0_d34dl1n3}` |
| 5 | The Upgrade | Proxy storage collision via delegatecall | `RKT{pr0xy_st0r4g3_c0ll1s10n_d3l3g4t3c4ll_pwn}` |
| 6 | The Shares | ERC-4626 first-depositor inflation | `RKT{3rc4626_f1rst_d3p0s1t0r_sh4r3_1nfl4t10n}` |

## Win condition per challenge (`Setup.isSolved()`)

| # | isSolved() returns true when |
|---|------------------------------|
| 1 | `address(vault).balance == 0` (pool drained) |
| 2 | `token.balanceOf(pool) == 0` (lending pool drained of tokens) |
| 3 | `address(treasury).balance == 0` (treasury swept) |
| 4 | `address(payments).balance == 0` (pot drained via replay) |
| 5 | `address(proxyWallet).balance == 0` (proxy swept after takeover) |
| 6 | victim has 0 shares **and** 0 assets **and** the vault is empty |

## How flags are released

The dispenser holds the flag strings (they are **not** in the contract
bytecode). For each challenge it calls `isSolved()` on the `Setup` via
`eth_call` (selector `0x64d98f6e`) against the chain, and returns the flag only
when it reads `true`. So a flag can only be obtained by genuinely solving the
challenge on-chain.

Self-check: `make check` runs [../scripts/verify.sh](../scripts/verify.sh)
(exploits + on-chain verification) → **ALL 6 FLAGS CAPTURED, exit 0**.
