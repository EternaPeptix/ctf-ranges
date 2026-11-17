FROM debian:12-slim
RUN apt-get update -qq && apt-get install -y -qq socat >/dev/null
COPY chall /chall
RUN chmod 755 /chall && printf 'TD{f0rmat_str1ng_arb1trary_wr1t3_n_sp3c}\n' > /flag && chmod 644 /flag
EXPOSE 9002
CMD ["socat", "-T120", "TCP-LISTEN:9002,reuseaddr,fork", "EXEC:/chall,stderr"]
