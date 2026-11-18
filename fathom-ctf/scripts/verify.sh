#!/usr/bin/env bash
# ============================================================================
#  fathom -- organizer self-check.
#  Runs the reference solver in a throwaway container on the puzzle network.
#  The solver uses GET /, POST /digits and POST /submit only, exactly like a
#  player. Needs only Docker. Exits 0 iff a TOKEN: line comes out.
#  The solver's output is tee'd to a log next to the Makefile; the log holds
#  the live polynomial and token, so it is removed again on exit.
# ============================================================================
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$DIR/../check.$$.log"
trap 'rm -f "$LOG"' EXIT

docker run --rm --network fathom_net -v "$DIR:/s:ro" python:3.12-slim python /s/solve.py | tee "$LOG"
rc=${PIPESTATUS[0]}

if [ "$rc" -eq 0 ] && grep -Eq '^TOKEN: FLAG\{[^}]+\}$' "$LOG"; then
  echo "[verify] PASS: polynomial recovered from digits of its root, token returned"
  exit 0
fi
echo "[verify] FAIL: token not recovered (solver exit code $rc)"
exit 1
