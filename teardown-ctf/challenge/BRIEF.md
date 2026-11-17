# Teardown — player brief

Five x86-64 pwnables. The binaries are in `challenges/<name>/chall` — reverse
them, then exploit the live service on the matching port. Flags `TD{...}`.

- `nc localhost 9001` … `9005` · scoreboard http://localhost:8506
- All binaries are **no-PIE**, **no stack canary**, NX on, glibc 2.36.

## The five

1. **The Overflow** (9001) — reads into a 64-byte buffer with no bound. There's a
   `win()` you never call.
2. **The Mirror** (9002) — echoes your input. *How* does it echo it?
3. **The Return** (9003) — overflow, NX, no `win()`. But the binary links
   `system` and has a `/bin/sh` string…
4. **The Lock** (9004) — a 16-byte serial is transformed and compared. Invert it.
5. **The Freelist** (9005) — a note heap manager. `delete` doesn't null the
   pointer.

## Hints

<details><summary>1 — ret2win</summary>
Offset to the saved return address is 72. Overwrite it with <code>win</code> —
and return through a <code>ret</code> gadget first so the stack stays 16-byte
aligned for the libc call inside <code>win</code>.</details>

<details><summary>2 — format string</summary>
<code>printf(buf)</code>. Your input is at direct arg offset <b>6</b>. Use
<code>%n</code> (pwntools <code>fmtstr_payload</code>) to write <code>0xc0ffee</code>
into the global <code>authed</code>.</details>

<details><summary>3 — ROP</summary>
Modern glibc has no <code>__libc_csu_init</code>, but the binary ships a leftover
<code>pop rdi ; ret</code>. Chain <code>pop rdi ; &"/bin/sh" ; system@plt</code>
(add a <code>ret</code> for alignment). All addresses are in the binary.</details>

<details><summary>4 — crackme</summary>
<code>t[i] = ((serial[i] ^ (0x41+i)) + 7) &amp; 0xff</code> compared to a fixed
target. Invert: <code>serial[i] = ((target[i]-7)&amp;0xff) ^ (0x41+i)</code>.</details>

<details><summary>5 — heap</summary>
glibc 2.32+ safe-linking mangles tcache <code>fd</code> as
<code>(pos&gt;&gt;12) ^ ptr</code>. Free a chunk, <b>view</b> it (UAF) to leak the
key (<code>pos&gt;&gt;12</code>), then edit a freed chunk's <code>fd</code> to
<code>key ^ &amp;hidden</code>. Allocate twice to get a chunk at
<code>&amp;hidden</code>, write <code>&amp;shell</code>, and <b>run</b>. (<code>hidden</code>
is 16-aligned so it passes the tcache alignment check.)</details>
