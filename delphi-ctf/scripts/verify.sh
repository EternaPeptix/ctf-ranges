#!/usr/bin/env bash
# ============================================================================
#  Delphi — automated solver / organizer self-check.
#  1) runs all six oracle exploits in a throwaway Foundry container on the net
#  2) asks the dispenser for each flag (it verifies isSolved() on-chain)
#  Needs only Docker. Exits 0 iff all six flags are released.
# ============================================================================
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
NET="${DLP_NET:-delphi_net}"
VOL="${DLP_VOL:-delphi_shared}"

echo "== running all six exploits in-network =="
docker run --rm --network "$NET" -v "$VOL:/shared:ro" \
  delphi-contracts bash /contracts/solve.sh

echo
echo "== verifying flags (dispenser checks isSolved() on-chain) =="
docker run --rm --network "$NET" -v "$DIR:/s:ro" \
  python:3.12-slim python3 /s/report.py
