#!/usr/bin/env bash
# ============================================================================
#  Teardown — automated solver / organizer self-check.
#  Builds a pwntools solver image and runs every exploit in a throwaway
#  container on the challenge network, submitting each flag to the scoreboard.
#  (The solver only parses the x86-64 binaries and talks over TCP, so it runs
#  natively.) Needs only Docker. Exits 0 iff all five flags are correct.
# ============================================================================
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
NET="${TD_NET:-teardown_net}"

docker build -q -t teardown-solver "$DIR/solver" >/dev/null
docker run --rm --network "$NET" teardown-solver
