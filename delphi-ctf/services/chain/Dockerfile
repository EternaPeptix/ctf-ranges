FROM ghcr.io/foundry-rs/foundry:latest
# A deterministic local dev chain. Default anvil accounts (well-known keys):
#   account[0] 0xf39F…2266  — deployer / protocol owner
#   account[1] 0x7099…79C8  — the attacker
EXPOSE 8545
ENTRYPOINT []
CMD ["anvil", "--host", "0.0.0.0", "--chain-id", "31337", "--accounts", "10", "--balance", "10000", "--silent"]
