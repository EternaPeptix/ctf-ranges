FROM ghcr.io/foundry-rs/foundry:latest
USER root
WORKDIR /contracts
ENTRYPOINT []

# Compile the project (downloads + caches solc 0.8.24 into the image).
COPY foundry.toml ./
COPY src ./src
COPY script ./script
RUN forge build

# Shell wrappers (changing these does not trigger a recompile).
COPY deploy.sh solve.sh ./

CMD ["bash", "/contracts/deploy.sh"]
