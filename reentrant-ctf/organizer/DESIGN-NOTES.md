# Reentrant — design notes (ORGANIZER)

## What makes this one different

The prior ranges in this series were all "attack a running service over
HTTP(ish)" — web apps, a jeopardy grid of web CVEs, an agentic platform. Reentrant
changes **the kind of artifact you attack**: there are no HTTP endpoints to
exploit. The surface is deployed **EVM bytecode**, the tools are `cast` / `forge`,
and the bugs are the canonical DeFi vulnerability classes. Different toolchain,
different mental model, same quality bar.

## Jeopardy, not a chain

DeFi exploits are naturally self-contained, so this is a board of six
**independent** challenges (like The Deep End / The Backlog) rather than a single
pivoting narrative. Each stands alone, is solvable in any order, and is graded by
its own on-chain `isSolved()`.

## Flags are earned, not findable

A recurring question for on-chain CTFs: where does the "flag" live? Putting a
string constant in the contract makes it extractable from bytecode without
solving. So here the **dispenser** (off-chain) holds the flags and releases each
one only after reading `isSolved() == true` from the chain via `eth_call`. The
contracts contain no flag strings. This mirrors a real CTF flag server and keeps
"solve to win" honest.

## Faithfulness

- Every target is a **minimal** re-implementation of one vulnerability class,
  small enough to read in a minute, with the omitted safeguard called out in a
  comment (the CEI order, the spot-price oracle, the missing initializer guard,
  the nonce-less digest, the colliding storage layout, the raw-balance share
  pricing). The docs name the famous incident each class echoes without claiming
  to reproduce that exact code.
- One `anvil` chain with the standard public dev accounts: account[0] is the
  protocol deployer/owner, account[1] is the attacker. Nothing depends on a
  secret the attacker shouldn't have — except the C4 voucher's **signing key**,
  which is organizer-only; the attacker receives only the signature, so the taught
  bug is replay, not key disclosure.

## Self-contained toolchain

The Foundry project vendors a tiny cheatcode shim ([Cheats.sol](../contracts/script/Cheats.sol))
instead of pulling `forge-std`, so the image builds with no git fetch. `solc
0.8.24` is pinned and cached into the contracts image at build time, so `make up`
and `make check` need no network access to compile.

## Organizer knobs

- Ports: `RPC_PORT` (default 8545), `SB_PORT` (default 8502).
- Flag strings live in [services/dispenser/app.py](../services/dispenser/app.py);
  rotate them per event freely (they're decoupled from the contracts).
- Challenge funding amounts and the attacker's token seed are in
  [Deploy.s.sol](../contracts/script/Deploy.s.sol) and the `*Setup` constructors.
- The attacker address is hard-coded (anvil account[1]) in the two challenges
  that seed it (C2, C6) and in the deploy voucher; change all three together if
  you re-point the attacker.

## Self-check

`make check` runs every exploit in a throwaway Foundry container on the chain
network, then a stdlib Python container asks the dispenser for each flag. Clean
result: **ALL 6 FLAGS CAPTURED, exit 0.**
