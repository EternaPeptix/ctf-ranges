#!/usr/bin/env bash
# ============================================================================
#  Obscura — automated solver / organizer self-check.
#  Runs all 5 exploits in a throwaway container on the challenge network, so it
#  reaches each widget by service name. Pure stdlib; exits 0 iff all 5 land.
# ============================================================================
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
NET="${OBS_NET:-obscura_net}"
docker run --rm --network "$NET" -v "$DIR:/s:ro" python:3.12-slim python /s/solve.py
