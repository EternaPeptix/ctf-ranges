#!/usr/bin/env bash
# ============================================================================
#  Cumulus — automated solver / organizer self-check.
#  Runs the full cloud kill-chain from a throwaway container on the platform
#  network and submits each flag to the scoreboard. Pure stdlib — needs only
#  Docker. Exits 0 iff all four flags land.
# ============================================================================
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
NET="${CML_NET:-cumulus_net}"
docker run --rm --network "$NET" -v "$DIR:/s:ro" python:3.12-slim python3 /s/solve.py
