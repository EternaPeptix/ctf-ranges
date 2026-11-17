#!/usr/bin/env bash
# ============================================================================
#  The Backlog — automated solver / organizer self-check.
#  Runs all 15 exploits in a throwaway container on the challenge network, so
#  it reaches each challenge by service name. Pure stdlib; exits 0 iff all land.
# ============================================================================
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
NET="${BL_NET:-backlog_net}"
docker run --rm --network "$NET" -v "$DIR:/s:ro" python:3.12-slim python /s/solve.py
