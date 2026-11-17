#!/usr/bin/env bash
# ============================================================================
#  Puppeteer — automated solver / organizer self-check.
#  Runs the full agentic kill-chain from a throwaway container on the platform
#  network (reaching the orchestrator by service name, and hosting the stage-5
#  poisoned model repo from inside that same container). Pure stdlib — needs
#  only Docker. Exits 0 iff all six flags land.
# ============================================================================
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
NET="${PUP_NET:-puppeteer_net}"
docker run --rm --network "$NET" -v "$DIR:/s:ro" python:3.12-slim \
  python /s/solve.py
