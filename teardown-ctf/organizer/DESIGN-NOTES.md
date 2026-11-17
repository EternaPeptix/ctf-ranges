# Teardown — design notes (ORGANIZER)

## Why this range

The series had deep coverage of web, crypto, EVM/DeFi, AI and DB/SSH — but **zero
binary exploitation or reverse engineering**, the oldest CTF pillar. Teardown
fills it with the canonical skill tree: a stack overflow, a format string, a ROP
chain, a reversing crackme, and a modern heap exploit, roughly in increasing
difficulty.

## Architecture

Each challenge is a real C program compiled **no-PIE, no stack canary** (so the
core bug is the lesson, not the mitigations), wrapped by `socat` on a TCP port —
the standard pwn-CTF delivery. The binaries ship **prebuilt** (players download
and reverse them, as in a real event). A pwntools solver connects to each port,
exploits it, and submits the flag to the scoreboard.

## Running x86-64 on an arm64 host

The host here is Apple-silicon (arm64), so the binaries (x86-64) run under
emulation. Decisions that follow from that:

- Challenge containers are pinned to `platform: linux/amd64`. docker-compose's
  build path couldn't cross-build the images, so `make up` builds them directly
  with `docker build --platform linux/amd64` ([scripts/build.sh](../scripts/build.sh)).
- The solver is **native** — it only parses the ELFs (pwntools `ELF`) and speaks
  TCP, so it needs no emulation.
- Under Rosetta the loader is **deterministic** (no ASLR in practice) and libc
  maps low (~`0x4000000000`), with all segments shown `r--p` (execution is
  translated). This mostly doesn't matter — except for a leak-based ret2libc
  (see C3).

## Per-challenge faithfulness notes

- **C1 / C2 / C4** are exactly the textbook bugs.
- **C3** is intended as ret2libc (leak `puts@libc`, resolve the base,
  `system("/bin/sh")`). On a real x86 target that's the solve. Under this
  emulator, the libc base is fixed *and* the `puts` leak truncates on a null byte
  in the (low) address — so the reference challenge ships a `/bin/sh` string and a
  linked `system@plt`, making it a self-contained **ret2plt** that is
  deterministic to auto-solve. Same ROP skill, no fragile leak.
- **C5** is deliberately **modern**: glibc 2.36, so the naive tcache-poison is
  blocked by **safe-linking**. The solve leaks the heap mangle key via a UAF
  `view` of a freed chunk, then forges the `fd`; the target pointer is
  16-byte-aligned to pass glibc's tcache alignment check. This teaches the
  current state of heap exploitation, not a 2018 one.

## Reliability

Emulated TCP occasionally drops a connection, so the solver retries each
challenge a few times. Two back-to-back `make check` runs capture all five.

## Organizer knobs

- Ports: `C1_PORT`..`C5_PORT` (9001–9005), `SB_PORT` (8506).
- Flags are in `challenges/*/Dockerfile` (planted at `/flag`) and in
  [../services/scoreboard/app.py](../services/scoreboard/app.py) for submission.
- To change a binary: edit `challenges/<name>/chall.c`, recompile for
  **linux/amd64 glibc 2.36** (e.g. `docker run --platform linux/amd64 debian:12-slim`
  with `gcc`, flags `-no-pie -fno-stack-protector`), drop the result at
  `challenges/<name>/chall` and `scripts/solver/bins/<cN>`, and rebuild.

## Self-check

`make check` builds the pwntools solver and runs every exploit on the challenge
network, submitting each flag. Clean result: **ALL 5 FLAGS CAPTURED, exit 0.**
