#!/usr/bin/env bash
# ============================================================================
#  resin -- organizer self-check.
#  Runs the reference solver in a throwaway container on the puzzle network.
#  The solver uses GET /, POST /resistance and POST /submit only, exactly like
#  a player. Needs only Docker. Exits 0 iff a TOKEN: line comes out.
#  The run is also kept in verify.log next to the Makefile.
# ============================================================================
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$(dirname "$DIR")/verify.log"

docker run --rm --network resin_net -v "$DIR:/s:ro" python:3.12-slim python /s/solve.py 2>&1 | tee "$LOG"
rc=${PIPESTATUS[0]}

if [ "$rc" -eq 0 ] && grep -Eq '^TOKEN: FLAG\{[^}]+\}$' "$LOG"; then
  echo "[verify] PASS: wiring recovered from the readings alone, token returned by /submit"
  exit 0
fi
echo "[verify] FAIL: token not recovered (solver exit code $rc)"
exit 1
