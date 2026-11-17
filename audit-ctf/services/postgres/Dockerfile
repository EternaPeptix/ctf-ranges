FROM postgres:16-alpine
# C1 — "The Query Plan": an internet-exposed Postgres with a weak superuser
# password. A superuser can run shell commands via COPY ... FROM PROGRAM
# (CVE-2019-9193 class), so the DB box is a shell. The flag lives on the host
# filesystem, readable by the postgres OS user.
RUN printf 'AUD{p0stgr3s_c0py_fr0m_pr0gr4m_sup3rus3r_rc3}\n' > /flag && chmod 644 /flag
COPY init.sql /docker-entrypoint-initdb.d/10-init.sql
