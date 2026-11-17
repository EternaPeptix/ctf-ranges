# The Gauntlet — flag sheet (ORGANIZER ONLY)

| # | Challenge | Technique | Flag |
|---|-----------|-----------|------|
| 1 | The Signet | ECDSA nonce reuse → key recovery | `GG{3cdsa_n0nc3_r3us3_pr1v4t3_k3y_r3c0v3ry}` |
| 2 | The Branch | Merkle second-preimage (leaf/node confusion) | `GG{m3rkl3_s3c0nd_pr31m4g3_l34f_n0d3_c0nfus10n}` |
| 3 | The Phantom | ecrecover returns address(0) | `GG{3cr3c0v3r_r3turns_z3r0_f0r_1nv4l1d_s1g}` |
| 4 | The Latch | EIP-1153 transient-storage reentrancy | `GG{31p1153_tr4ns13nt_cr0ss_funct10n_r33ntr4ncy}` |
| 5 | The Dice | Weak randomness (prevrandao) | `GG{pr3vr4nd40_w34k_r4nd0mn3ss_s4m3_bl0ck}` |
| 6 | The Clash | Selector/facet delegatecall hijack | `GG{s3l3ct0r_f4c3t_h1j4ck_d3l3g4t3c4ll_r0ut3r}` |
| 7 | The Keystone | BN254 pairing-verifier bypass | `GG{bn254_p41r1ng_v3r1f13r_z3r0_pr00f_f0rg3ry}` |

## Win condition per challenge (`Setup.isSolved()`)

| # | isSolved() true when |
|---|----------------------|
| 1 | `address(vault).balance == 0` (forged-signature withdrawal) |
| 2 | `address(vault).balance == 0` (second-preimage claim) |
| 3 | `address(vault).balance == 0` (ecrecover==0 bypass) |
| 4 | `address(bank).balance == 0` (cross-function reentrancy double-spend) |
| 5 | `address(casino).balance == 0` (predicted roll) |
| 6 | `address(router).balance == 0` (facet hijack) |
| 7 | `address(vault).balance == 0` (forged pairing proof) |

## How flags are released

The dispenser holds the flag strings (not in contract bytecode). For each
challenge it calls `isSolved()` via `eth_call` (selector `0x64d98f6e`) and
returns the flag only when it reads `true`.

## C1 provenance

The two leaked signatures are a genuine secp256k1 nonce-reuse pair. The signer
address `0x97b9210c81f67a7FCC3811552BcBB0ECc18ad347` is `addr(d)` for the private
key `d` that `(R,S1,H1)`/`(R,S2,H2)` expose; the solver recovers exactly that `d`.
(`d`, kept off-chain, is `0x4f3edf983ac636a65a842ce7c78d9aa706d3b113b37e3b1b5e3c9a1b2c7d8e90`.)

Self-check: `make check` → **ALL 7 FLAGS CAPTURED, exit 0**.
