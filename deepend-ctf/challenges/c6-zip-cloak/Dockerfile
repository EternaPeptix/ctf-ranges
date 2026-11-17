FROM rust:1.83-slim
WORKDIR /app
COPY Cargo.toml .
COPY src ./src
RUN cargo build --release
EXPOSE 80
CMD ["./target/release/c6"]
