#!/usr/bin/env bash
# ============================================================================
#  The Gauntlet — automated solver / organizer self-check.
#  1) runs all seven exploits in a throwaway Foundry container on the chain net
#  2) asks the dispenser for each flag (it verifies isSolved() on-chain)
#  Needs only Docker. Exits 0 iff all seven flags are released.
# ============================================================================
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
NET="${GNT_NET:-gauntlet_net}"
VOL="${GNT_VOL:-gauntlet_shared}"
echo "== running all seven exploits in-network =="
docker run --rm --network "$NET" -v "$VOL:/shared:ro" gauntlet-contracts bash /contracts/solve.sh
echo
echo "== verifying flags (dispenser checks isSolved() on-chain) =="
docker run --rm --network "$NET" -v "$DIR:/s:ro" python:3.12-slim python3 /s/report.py
