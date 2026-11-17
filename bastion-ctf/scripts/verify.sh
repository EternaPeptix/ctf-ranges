#!/usr/bin/env bash
# ============================================================================
#  Bastion CTF — automated solver / organizer self-check.
#  Pure python3 stdlib (MD5 length extension is hand-rolled), no pip needed.
#      WEB_PORT=8093 ./scripts/verify.sh
#  Exits 0 only if all 5 flags are captured.
# ============================================================================
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$DIR/solve.py" "http://localhost:${WEB_PORT:-8080}"
