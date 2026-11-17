# Teardown — flag sheet (ORGANIZER ONLY)

| # | Challenge | Technique | Flag |
|---|-----------|-----------|------|
| 1 | The Overflow | ret2win stack overflow | `TD{r3t2w1n_st4ck_sm4sh_cl4ss1c_0v3rfl0w}` |
| 2 | The Mirror | format-string `%n` write | `TD{f0rmat_str1ng_arb1trary_wr1t3_n_sp3c}` |
| 3 | The Return | ROP → `system('/bin/sh')` (ret2plt) | `TD{r3t2l1bc_r0p_l34k_g0t_c4ll_syst3m}` |
| 4 | The Lock | RE crackme (invert the transform) | `TD{r3v3rs3_th3_s3r14l_x0r_tr4nsf0rm_cr4ckm3}` |
| 5 | The Freelist | heap UAF → tcache safe-linking poison → RCE | `TD{h34p_uaf_tc4ch3_p01s0n_fptr_0v3rwr1t3}` |

## Where each flag lives

All flags are in `/flag` inside each challenge container; the exploit reads it
(via `win()`, a popped shell, or `cat`). Challenge 4's flag is read by `win()` on
the correct serial — it is **not** in the binary (only the target bytes are).

## Key facts (for grading / hints)

- **C1 / C3**: offset to the saved return address is **72** (`buf[64]` + saved rbp).
- **C2**: format-string direct arg offset is **6**; target global `authed` must
  become `0xc0ffee`.
- **C3**: the binary ships a `pop rdi ; ret` gadget (`__gadget`), a `/bin/sh`
  string (`shellcmd`), and a linked `system@plt`.
- **C4**: `serial = "g0_r3v3rs3_m3_pl"`; `target` is in the binary; invert
  `t[i]=((s[i]^(0x41+i))+7)&0xff`.
- **C5**: glibc 2.36 tcache. Leak the safe-linking key via a UAF `view` of a
  freed chunk, then poison. `hidden` is `__attribute__((aligned(16)))`.

Self-check: `make check` runs [../scripts/solver/solve.py](../scripts/solver/solve.py)
(a pwntools solver) → **ALL 5 FLAGS CAPTURED, exit 0** (it retries a few times to
absorb the emulator's occasional connection flake).
