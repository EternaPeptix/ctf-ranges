# The Audit — findings & flag sheet (ORGANIZER ONLY)

| # | Finding | Class | Flag |
|---|---------|-------|------|
| 1 | The Query Plan | PostgreSQL `COPY FROM PROGRAM` RCE (CVE-2019-9193 class) | `AUD{p0stgr3s_c0py_fr0m_pr0gr4m_sup3rus3r_rc3}` |
| 2 | The Dump | MySQL `FILE` priv + `secure_file_priv=""` `LOAD_FILE` | `AUD{mysql_f1l3_pr1v_l04d_f1l3_s3cur3_f1l3_pr1v}` |
| 3 | The Catalog | SQLite UNION injection | `AUD{sql1t3_un10n_1nj3ct10n_sql1t3_m4st3r_dump}` |
| 4 | The Backdoor Key | Leaked SSH private key (exposed backup) | `AUD{ssh_l34k3d_pr1v4t3_k3y_dbadm1n_f00th0ld}` |
| 5 | The Audit Trail | SSH + DB log forensics | `AUD{ssh_brut3f0rc3_db_3xf1l_4ud1t_l0g_f0r3ns1cs}` |

## Where each flag lives

| # | Planted | Reached via |
|---|---------|-------------|
| 1 | `/flag` on the postgres container | `COPY t FROM PROGRAM 'cat /flag'` as superuser `postgres`/`postgres` |
| 2 | `/flag` on the mariadb container | `SELECT LOAD_FILE('/flag')` as `appuser` (has `FILE`; `secure_file_priv=""`) |
| 3 | `ops_secret_vault` table (SQLite) in the webapp | UNION injection on `/api/product?id=` |
| 4 | `/flag` on the ssh container | SSH as `dbadmin` with the key leaked at `webapp:/backup/id_ed25519` |
| 5 | encoded in the scoreboard's generated `pg_audit.log` | correlate the SSH `Accepted publickey` time with the exfil DB session; base64-decode its `c=` chunks |

## Credentials & config (intentional weaknesses)

- Postgres: superuser `postgres` / `postgres`.
- MariaDB: `appuser` / `appuser` with `GRANT FILE`; `secure_file_priv=` (empty).
- SSH: `dbadmin`; pubkey login with the leaked `id_ed25519` (the matching
  `authorized_keys` ships in the ssh image). Password `dbadmin` exists only to
  unlock the account for pubkey login; password auth is disabled in `sshd_config`.
- The leaked keypair is committed under `services/webapp/backup/` (private) and
  `services/ssh/authorized_keys` (public) — regenerate both together to rotate.

Self-check: `make check` runs [../scripts/solver/solve.py](../scripts/solver/solve.py)
in-network (DB + SSH + HTTP clients) → **ALL 5 FLAGS CAPTURED, exit 0**.
