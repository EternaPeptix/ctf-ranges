#!/usr/bin/env bash
# ============================================================================
#  quorum -- organizer self-check.
#  Runs the reference solver in a throwaway container on the puzzle network.
#  The solver uses GET /, POST /residue and POST /submit only, exactly like a
#  player. Needs only Docker. Exits 0 iff a TOKEN: line comes out.
#  The solver's output of the last run is kept in verify.log (gitignored).
# ============================================================================
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$DIR/../verify.log"

docker run --rm --network quorum_net -v "$DIR:/s:ro" python:3.12-slim python /s/solve.py | tee "$LOG"
rc=${PIPESTATUS[0]}

if [ "$rc" -eq 0 ] && grep -Eq '^TOKEN: FLAG\{[^}]+\}$' "$LOG"; then
  echo "[verify] PASS: N recovered despite the liars, token returned by /submit"
  exit 0
fi
echo "[verify] FAIL: token not recovered (solver exit code $rc)"
exit 1
