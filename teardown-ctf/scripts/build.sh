#!/usr/bin/env bash
# Build + start the range. The challenge binaries are x86-64 and ship prebuilt
# (challenges/*/chall), so the images only need to be assembled for linux/amd64.
# docker-compose's build path can't cross-build here, so we build the images
# directly (which honors --platform) and then just run them.
set -eu
DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR"

for c in c1-overflow c2-format c3-rop c4-crackme c5-heap; do
    docker build --platform linux/amd64 -q -t "teardown-${c%%-*}" "challenges/$c" >/dev/null
done
docker build -q -t teardown-scoreboard services/scoreboard >/dev/null

docker compose up -d --no-build
