#!/usr/bin/env bash
# ============================================================================
#  The Audit — automated solver / organizer self-check.
#  Builds a solver image (DB + SSH + HTTP clients) and runs every exploit in a
#  throwaway container on the challenge network, submitting each flag to the
#  scoreboard. Needs only Docker. Exits 0 iff all five flags are correct.
# ============================================================================
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
NET="${AUD_NET:-audit_net}"

docker build -q -t audit-solver "$DIR/solver" >/dev/null
docker run --rm --network "$NET" audit-solver
