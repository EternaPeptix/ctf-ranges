#!/bin/bash
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
SOLVER_DIR=/Users/jeweled/loom-training/range-gt
cp "$DIR/../solution/solve.py" "$SOLVER_DIR/p2s_solve.py"
docker run --rm --network php2shell_net \
  -v "$SOLVER_DIR:/s:ro" python:3.12-slim python /s/p2s_solve.py | tee /tmp/php2shell-verify.log
grep -q '^TOKEN: FLAG{' /tmp/php2shell-verify.log && echo "[verify] PASS: session upload_progress injection + /raw.php LFI, flag recovered" && exit 0
echo "[verify] FAIL" && exit 1
