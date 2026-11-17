FROM debian:12-slim
RUN apt-get update -qq && apt-get install -y -qq socat >/dev/null
COPY chall /chall
RUN chmod 755 /chall && printf 'TD{r3t2w1n_st4ck_sm4sh_cl4ss1c_0v3rfl0w}\n' > /flag && chmod 644 /flag
EXPOSE 9001
CMD ["socat", "-T120", "TCP-LISTEN:9001,reuseaddr,fork", "EXEC:/chall,stderr"]
