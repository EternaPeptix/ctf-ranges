#!/usr/bin/env bash
# Runs all six exploits against the deployed challenges (as the attacker,
# anvil account[1]). Reads Setup addresses from /shared/addrs.env.
set -u
RPC=${RPC_URL:-http://chain:8545}
# anvil account[1] — the attacker
PK=0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d

# shellcheck disable=SC1091
source /shared/addrs.env

run() {
  local name="$1" setup="$2"
  echo "── $name  ($setup)"
  if SETUP="$setup" forge script "script/solve/$name.s.sol:$name" \
        --rpc-url "$RPC" --private-key "$PK" --broadcast >"/tmp/$name.log" 2>&1; then
    echo "   exploit broadcast"
  else
    echo "   FAILED:"; tail -8 "/tmp/$name.log" | sed 's/^/     /'
  fi
}

run SolveC1 "$C1_SETUP"
run SolveC2 "$C2_SETUP"
run SolveC3 "$C3_SETUP"
run SolveC4 "$C4_SETUP"
run SolveC5 "$C5_SETUP"
run SolveC6 "$C6_SETUP"
echo "── all exploits attempted"
