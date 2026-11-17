# Teardown

> Binary exploitation & reverse engineering — the classic CTF pillar the series
> was missing.

**Teardown** is five x86-64 pwnables served over TCP, from a beginner stack
overflow up to a modern-glibc heap exploit. Flags `TD{...}`.

| # | Challenge | Technique | Port |
|---|-----------|-----------|------|
| 1 | **The Overflow** | **ret2win** — stack buffer overflow overwrites the return address to a `win()` function | 9001 |
| 2 | **The Mirror** | **format string** — `printf(user_input)` → `%n` writes to flip a global and reach `shell()` | 9002 |
| 3 | **The Return** | **ROP** — no win function; chain `pop rdi` → `system("/bin/sh")` (ret2plt) | 9003 |
| 4 | **The Lock** | **reverse engineering** — recover the serial by inverting a byte-transform crackme | 9004 |
| 5 | **The Freelist** | **heap UAF → tcache poisoning** — defeat glibc 2.32+ **safe-linking** (leak the heap, forge a chunk) to overwrite a function pointer | 9005 |

Each challenge is a real compiled binary (`challenges/*/chall`, no-PIE, glibc
2.36) wrapped by `socat`. The binaries ship prebuilt — download them, reverse
them, and write your exploit, exactly like a real CTF.

## Run it

```bash
make up        # build + start all five challenges + the scoreboard
make check     # run the full pwntools solver and prove all 5 flags, exit 0
make down      # stop + remove everything
```

- **Scoreboard:** http://localhost:8506 — the five challenges + flag submission
- **Challenges:** `nc localhost 9001` … `9005`

## How you play

Grab a binary (it's in `challenges/<name>/chall`), reverse it with your tools of
choice (Ghidra / gdb / objdump / pwntools), and pop the service:

```bash
nc localhost 9001
# ... or write a pwntools exploit against localhost:9001
```

See [challenge/BRIEF.md](challenge/BRIEF.md) for hints. The reference exploits are
[scripts/solver/solve.py](scripts/solver/solve.py).

## Notes on the environment

The binaries are **x86-64**; on an Apple-silicon host the challenge containers
run under emulation (Rosetta), pinned to `platform: linux/amd64`. The solver only
parses the binaries and talks over TCP, so it runs natively. One consequence:
under the emulator the loader is deterministic, which the C3 reference solver
leans on (a real target would leak libc — see the design notes).

## Organizer

- [organizer/FLAGS.md](organizer/FLAGS.md) — the flag sheet
- [organizer/SOLUTION.md](organizer/SOLUTION.md) — the full exploit walkthrough
- [organizer/DESIGN-NOTES.md](organizer/DESIGN-NOTES.md) — why it's built this way

> ⚠️ Deliberately vulnerable training binaries. Don't deploy them anywhere
> reachable.
