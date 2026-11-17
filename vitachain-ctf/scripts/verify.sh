#!/usr/bin/env bash
# ============================================================================
#  VitaChain — automated solver / organizer self-check.
#  Runs all 6 exploits in a throwaway container on the challenge network, so it
#  reaches each widget by service name. Pure stdlib; exits 0 iff all 6 land.
#  (c3 is a real concurrency race; c4 drives a DNS-rebind against the in-net imds.)
# ============================================================================
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
NET="${VITA_NET:-vitachain_net}"
docker run --rm --network "$NET" -v "$DIR:/s:ro" python:3.12-slim python /s/solve.py
