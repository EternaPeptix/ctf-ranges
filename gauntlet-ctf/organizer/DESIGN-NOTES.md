# The Gauntlet — design notes (ORGANIZER)

## The brief: the hardest range

Reentrant and Delphi lived in the "textbook bug" tier — real classes, but ones a
good auditor spots on sight. The Gauntlet deliberately leaves that tier for
**research-grade EVM and cryptographic primitives**: genuine cryptanalysis
(nonce reuse), a hash-structure attack that has fooled production Merkle drops,
an `ecrecover` footgun, a bug in *brand-new* Cancun transient storage, and — as
the capstone — forging a zero-knowledge proof past a broken pairing verifier.
Nothing here falls to a single obvious call; each one requires understanding the
primitive.

## Difficulty gradient

- **#3 / #5** are the on-ramps: an `ecrecover` quirk and predictable randomness —
  one-liner exploits *once you know the trap*.
- **#2 / #6** are subtle structural bugs (Merkle second-preimage, unprotected
  facet registration) that have drained real protocols.
- **#4** is bleeding-edge: cross-function reentrancy past an EIP-1153 lock that
  looks airtight.
- **#1** is real cryptanalysis — recover a private key from two signatures.
- **#7**, the capstone, is the hardest: a pairing-based proof forgery. You must
  understand bilinearity and the BN254 precompile to see that `C = −A` satisfies
  the under-constrained verifier.

## Faithfulness

- Each target is a minimal model with the omitted safeguard named in a comment
  (never reuse `k`; domain-separate leaves from nodes; reject `ecrecover==0`; a
  global lock not a per-selector one; commit-reveal / VRF; `onlyOwner` on facet
  registration; a complete Groth16 check with subgroup/zero validation).
- **#1 uses a genuine secp256k1 nonce-reuse pair.** The leaked `(R,S1,H1)` /
  `(R,S2,H2)` were generated off-chain (see [FLAGS.md](FLAGS.md)) so that the
  signer address really is `addr(d)`; the solver recovers exactly that `d` with
  on-chain modular arithmetic (`mulmod`/`addmod` + the modexp precompile) and
  signs with it. No shortcut — it is the real attack.
- **#7 uses the real `ecPairing` precompile (0x08)** via the canonical BN254
  `Pairing` library; the forgery is a true pairing identity, not a mock.

## Chain requirements

The chain is pinned to the **Cancun** hardfork (`anvil --hardfork cancun`,
`evm_version = "cancun"`) so EIP-1153 `tstore`/`tload` (#4) and the BN254
precompiles (#7) behave as on mainnet. Everything else is the same proven harness
as Reentrant/Delphi: a self-contained Foundry project (a tiny vendored cheatcode
shim, `solc 0.8.24` cached into the image) and the dispenser that releases a flag
only after reading `isSolved()` on-chain.

## Flags are earned, not findable

Flag strings live in the dispenser, not in bytecode; each is released only after
`isSolved()` reads true. Same model as the other on-chain ranges.

## Organizer knobs

- Ports: `RPC_PORT` (default 8549), `SB_PORT` (default 8504).
- Flag strings: [../services/dispenser/app.py](../services/dispenser/app.py)
  (decoupled from the contracts).
- Funding amounts are in the `Deploy` script; the attacker address (anvil
  account[1]) is hard-coded where a solver contract needs it.
- To regenerate #1's nonce-reuse data, re-run the off-chain generator and update
  the five constants in `C1Signet.sol` plus the signer address.

## Self-check

`make check` runs every exploit in a throwaway Foundry container on the chain
network, then a stdlib Python container asks the dispenser for each flag. Clean
result: **ALL 7 FLAGS CAPTURED, exit 0.**
