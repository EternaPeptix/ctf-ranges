#!/usr/bin/env bash
# ============================================================================
#  treadle -- organizer self-check.
#  Runs the reference solver in a throwaway container on the puzzle network.
#  The solver reconstructs the hidden machine from /run and /conjecture only.
#  Needs only Docker. Exits 0 iff the completion token is recovered.
# ============================================================================
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$(mktemp)"
trap 'rm -f "$LOG"' EXIT

docker run --rm --network treadle_net -v "$DIR:/s:ro" python:3.12-slim python /s/solve.py | tee "$LOG"
rc=${PIPESTATUS[0]}

if [ "$rc" -eq 0 ] && grep -Eq '^TOKEN: FLAG\{[^}]+\}$' "$LOG"; then
  echo "[verify] PASS: machine reconstructed exactly, token recovered"
  exit 0
fi
echo "[verify] FAIL: token not recovered (solver exit code $rc)"
exit 1
