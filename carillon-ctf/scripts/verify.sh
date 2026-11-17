#!/usr/bin/env bash
# ============================================================================
#  carillon -- organizer self-check.
#  Runs the reference solver in a throwaway container on the puzzle network.
#  The solver uses GET / and POST /run only, exactly like a player.
#  Needs only Docker. Exits 0 iff a TOKEN: line comes out.
# ============================================================================
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$(mktemp)"
trap 'rm -f "$LOG"' EXIT

docker run --rm --network carillon_net -v "$DIR:/s:ro" python:3.12-slim python /s/solve.py | tee "$LOG"
rc=${PIPESTATUS[0]}

if [ "$rc" -eq 0 ] && grep -Eq '^TOKEN: FLAG\{[^}]+\}$' "$LOG"; then
  echo "[verify] PASS: special command found by trying, token read out of the drawer"
  exit 0
fi
echo "[verify] FAIL: token not recovered (solver exit code $rc)"
exit 1
