FROM debian:12-slim
RUN apt-get update -qq && apt-get install -y -qq socat >/dev/null
COPY chall /chall
RUN chmod 755 /chall && printf 'TD{r3t2l1bc_r0p_l34k_g0t_c4ll_syst3m}\n' > /flag && chmod 644 /flag
EXPOSE 9003
CMD ["socat", "-T120", "TCP-LISTEN:9003,reuseaddr,fork", "EXEC:/chall,stderr"]
