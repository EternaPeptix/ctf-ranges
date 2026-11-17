#!/usr/bin/env bash
# ============================================================================
#  synapse -- organizer self-check.
#  Runs the reference solver in a throwaway container on the puzzle network.
#  The solver reconstructs f from /eval queries only and submits it to /verify.
#  Needs only Docker. Exits 0 iff the completion token is recovered.
# ============================================================================
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$(mktemp)"
trap 'rm -f "$LOG"' EXIT

docker run --rm --network synapse_net -v "$DIR:/s:ro" python:3.12-slim python /s/solve.py | tee "$LOG"
rc=${PIPESTATUS[0]}

if [ "$rc" -eq 0 ] && grep -Eq '^TOKEN: FLAG\{[^}]+\}$' "$LOG"; then
  echo "[verify] PASS: f reconstructed exactly, token recovered"
  exit 0
fi
echo "[verify] FAIL: token not recovered (solver exit code $rc)"
exit 1
