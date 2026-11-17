#!/usr/bin/env bash
# ============================================================================
#  Keyhaven CTF — automated end-to-end solver / organizer self-check.
#  Runs the Python solver in a throwaway container on the edge network, so it
#  reaches the published edge exactly as a remote player would and needs nothing
#  installed on the host but Docker. Exits 0 only if all 7 core flags land.
# ============================================================================
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
NET="${KH_NET:-kh_edge}"
docker run --rm --network "$NET" -v "$DIR:/s:ro" python:3.12-slim \
  sh -c 'pip install -q "ecdsa==0.19.0" >/dev/null 2>&1 && python /s/solve.py http://app.keyhaven.example'
