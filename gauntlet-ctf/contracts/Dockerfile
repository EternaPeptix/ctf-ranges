FROM ghcr.io/foundry-rs/foundry:latest
USER root
WORKDIR /contracts
ENTRYPOINT []
COPY foundry.toml ./
COPY src ./src
COPY script ./script
RUN forge build
COPY deploy.sh solve.sh ./
CMD ["bash", "/contracts/deploy.sh"]
