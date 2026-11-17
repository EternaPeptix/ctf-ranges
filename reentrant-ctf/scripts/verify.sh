#!/usr/bin/env bash
# ============================================================================
#  Reentrant — automated solver / organizer self-check.
#  1) runs all six exploits in a throwaway Foundry container on the chain net
#  2) asks the dispenser for each flag (it verifies isSolved() on-chain)
#  Needs only Docker. Exits 0 iff all six flags are released.
# ============================================================================
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
NET="${RKT_NET:-reentrant_net}"
VOL="${RKT_VOL:-reentrant_shared}"

echo "== running all six exploits in-network =="
docker run --rm --network "$NET" -v "$VOL:/shared:ro" \
  reentrant-contracts bash /contracts/solve.sh

echo
echo "== verifying flags (dispenser checks isSolved() on-chain) =="
docker run --rm --network "$NET" -v "$DIR:/s:ro" \
  python:3.12-slim python3 /s/report.py
