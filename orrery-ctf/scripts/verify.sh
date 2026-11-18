#!/usr/bin/env bash
# ============================================================================
#  orrery -- organizer self-check.
#  Runs the reference solver in a throwaway container on the puzzle network.
#  The solver works from GET /, 32 x POST /eval and one POST /submit only.
#  Needs only Docker. Output is kept in verify.log next to the Makefile.
#  Exits 0 iff the solver printed a TOKEN: line.
#
#  The solver spends the whole evaluation budget, so this needs an instance
#  with all 32 evaluations left: `make check` provides one, `make reset` too.
# ============================================================================
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$(cd "$DIR/.." && pwd)/verify.log"

docker run --rm --network orrery_net -v "$DIR:/s:ro" python:3.12-slim python /s/solve.py 2>&1 | tee "$LOG"
rc=${PIPESTATUS[0]}

if [ "$rc" -eq 0 ] && grep -Eq '^TOKEN: [A-Z]+\{[^}]+\}$' "$LOG"; then
  echo "[verify] PASS: polynomial reconstructed from 32 evaluations, token recovered"
  exit 0
fi
echo "[verify] FAIL: token not recovered (solver exit code $rc)"
exit 1
