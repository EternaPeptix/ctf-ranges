FROM mariadb:11
# C2 — "The Dump": an app DB user granted the FILE privilege, with
# secure_file_priv left empty (an audit misconfig), so LOAD_FILE() reads any
# world-readable file on the DB host — including the flag.
RUN printf 'AUD{mysql_f1l3_pr1v_l04d_f1l3_s3cur3_f1l3_pr1v}\n' > /flag && chmod 644 /flag
COPY ctf.cnf /etc/mysql/conf.d/99-ctf.cnf
COPY init.sql /docker-entrypoint-initdb.d/10-init.sql
ENV MARIADB_ROOT_PASSWORD=root
ENV MARIADB_DATABASE=ctf
