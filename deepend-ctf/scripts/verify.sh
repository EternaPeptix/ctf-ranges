#!/usr/bin/env bash
# ============================================================================
#  The Deep End — automated solver / organizer self-check.
#  Runs all 6 exploits in a throwaway container on the challenge network
#  (reaching challenges by service name). Needs only Docker. Exits 0 iff all land.
# ============================================================================
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
NET="${DE_NET:-deepend_net}"
docker run --rm --network "$NET" -v "$DIR:/s:ro" python:3.12-slim \
  sh -c 'pip install -q "ecdsa==0.19.0" >/dev/null 2>&1 && python /s/solve.py'
