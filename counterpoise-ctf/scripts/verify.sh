#!/usr/bin/env bash
# ============================================================================
#  counterpoise -- organizer self-check.
#  Runs the reference solver in a throwaway container on the puzzle network.
#  The solver uses GET /, POST /weigh and POST /submit only, exactly like a
#  player, and stays inside the 255-question budget.
#  Needs only Docker. Exits 0 iff a TOKEN: line comes out.
# ============================================================================
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$(cd "$DIR/.." && pwd)/verify.log"

docker run --rm --network counterpoise_net -v "$DIR:/s:ro" python:3.12-slim python /s/solve.py 2>&1 | tee "$LOG"
rc=${PIPESTATUS[0]}

if [ "$rc" -eq 0 ] && grep -Eq '^TOKEN: FLAG\{[^}]+\}$' "$LOG"; then
  echo "[verify] PASS: hidden vector recovered within the question budget, token released"
  exit 0
fi
echo "[verify] FAIL: token not recovered (solver exit code $rc)"
exit 1
