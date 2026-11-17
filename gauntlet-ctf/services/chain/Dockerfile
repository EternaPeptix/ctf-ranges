FROM ghcr.io/foundry-rs/foundry:latest
# Pinned to the Cancun hardfork so EIP-1153 transient storage (tstore/tload) and
# the BN254 precompiles are available.
#   account[0] 0xf39F…2266  — deployer / protocol owner
#   account[1] 0x7099…79C8  — the attacker
EXPOSE 8545
ENTRYPOINT []
CMD ["anvil", "--host", "0.0.0.0", "--chain-id", "31337", "--hardfork", "cancun", "--accounts", "10", "--balance", "10000", "--silent"]
