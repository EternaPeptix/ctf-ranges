# Delphi — design notes (ORGANIZER)

## What this range is

Delphi takes the single deepest challenge in **Reentrant** — "The Oracle" — and
expands it into a whole range. Price-oracle manipulation is arguably *the*
defining DeFi attack class, and it has far more depth than one challenge can
show: a clamped feed, a stale feed, a time-weighted average, a virtual price read
mid-reentrancy, a naively-priced LP token, and a decimals mismatch are six
genuinely different mental models, not six flavors of one trick.

It reuses Reentrant's proven infrastructure (one `anvil` chain, a self-contained
Foundry project, and the dispenser that releases flags only after verifying
`isSolved()` on-chain), so the plumbing is identical and the novelty is all in
the challenges.

## Depth gradient

The board roughly escalates: #1/#2/#6 are "trust the wrong number" bugs (a clamp,
a stale timestamp, a decimals mismatch) solvable in a couple of calls; #3 adds
**time** (you must pump, hold, and let the window elapse); #5 adds a **flash
loan** and atomic imbalance/restore; #4 — the capstone — is **read-only
reentrancy**, the most modern and most-missed of the set, where the exploit lives
in the window *inside* a `removeLiquidity` call.

## Faithfulness

- Each target is a minimal model of the mechanic with the omitted safeguard
  called out in a comment (the `minAnswer` clamp, the absent `updatedAt` check,
  the short TWAP window, the balances-before-callback ordering, the spot LP
  price, the `/1e8` scaling). The docs name the real incident each echoes.
- A dev chain has no live market, so "the asset crashed" / "the feed froze" is
  simulated by the Setup calling `setAnswer` / `setAnswerStale` on the mock
  aggregator. What's being taught is the *protocol's* trust in that value, which
  is the real bug in every one of these incidents.
- The flash loan in #5 is a real same-tx-repayment lender, and #5's attacker
  restores the pool and repays — the authentic Warp/Cheese shape.

## The one non-obvious operational detail

**The Window (#3) needs the chain clock advanced** past the 600s TWAP window
between the manipulation and the drain. On anvil that's
`cast rpc evm_increaseTime 700` + `evm_mine`; the solver
([../contracts/solve.sh](../contracts/solve.sh)) does this between `SolveC3a` and
`SolveC3b`. A `forge script`'s `vm.warp` only affects the script's own EVM, not
the live chain, which is why this is an RPC call, not a cheatcode.

## Flags are earned, not findable

Flag strings live in the dispenser, not in contract bytecode; each is released
only after `isSolved()` reads true on-chain. Same model as Reentrant.

## Organizer knobs

- Ports: `RPC_PORT` (default 8547), `SB_PORT` (default 8503).
- Flag strings: [../services/dispenser/app.py](../services/dispenser/app.py)
  (decoupled from the contracts; rotate freely).
- Funding amounts, the attacker's seeds, and the TWAP `PERIOD` are in the `*Setup`
  constructors and `TwapOracle`. The attacker address (anvil account[1]) is
  hard-coded in the Setups that seed it; change those together if you re-point it.

## Self-check

`make check` runs every exploit in a throwaway Foundry container on the chain
network (advancing the clock for #3), then a stdlib Python container asks the
dispenser for each flag. Clean result: **ALL 6 FLAGS CAPTURED, exit 0.**
