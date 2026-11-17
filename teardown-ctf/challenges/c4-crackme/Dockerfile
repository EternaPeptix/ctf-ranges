FROM debian:12-slim
RUN apt-get update -qq && apt-get install -y -qq socat >/dev/null
COPY chall /chall
RUN chmod 755 /chall && printf 'TD{r3v3rs3_th3_s3r14l_x0r_tr4nsf0rm_cr4ckm3}\n' > /flag && chmod 644 /flag
EXPOSE 9004
CMD ["socat", "-T120", "TCP-LISTEN:9004,reuseaddr,fork", "EXEC:/chall,stderr"]
