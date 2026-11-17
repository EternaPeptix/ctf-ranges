FROM debian:12-slim
RUN apt-get update -qq && apt-get install -y -qq socat >/dev/null
COPY chall /chall
RUN chmod 755 /chall && printf 'TD{h34p_uaf_tc4ch3_p01s0n_fptr_0v3rwr1t3}\n' > /flag && chmod 644 /flag
EXPOSE 9005
CMD ["socat", "-T120", "TCP-LISTEN:9005,reuseaddr,fork", "EXEC:/chall,stderr"]
