#!/usr/bin/env bash
# One-shot deployer: wait for the chain, deploy all challenges, write addrs.env.
set -e
RPC=${RPC_URL:-http://chain:8545}
# anvil account[0] — the protocol deployer/owner
PK=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80

echo "[deployer] waiting for chain at $RPC ..."
for _ in $(seq 1 60); do
  cast block-number --rpc-url "$RPC" >/dev/null 2>&1 && break
  sleep 1
done

echo "[deployer] deploying challenges ..."
forge script script/Deploy.s.sol:Deploy \
  --rpc-url "$RPC" --private-key "$PK" --broadcast

echo "[deployer] wrote /shared/addrs.env:"
cat /shared/addrs.env
echo "[deployer] done."
