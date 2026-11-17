# The Audit — design notes (ORGANIZER)

## Why this slice exists

The series had no database challenges and no SSH challenges. This small slice
fills both gaps at once, as a blend: four live exploits against **real daemons**
(PostgreSQL, MariaDB, SQLite, OpenSSH — not re-implementations) plus one forensic
"audit the logs" challenge, so it covers DB misconfiguration, DB injection, key
hygiene, and incident response in one coherent audit narrative.

## Harness

Unlike the recent on-chain ranges, these are network services, so it uses the
Docker + scoreboard + solver pattern (like The Backlog / Puppeteer): a
`docker-compose` of five services, a scoreboard that also serves the forensic
logs, and a multi-driver Python solver (`psycopg2` / `PyMySQL` / `paramiko` /
`requests`) that exploits everything in-network and submits each flag. The
scoreboard holds the flag strings and verifies submissions.

## Faithfulness

- **C1 / C2** use the *actual* `postgres:16-alpine` and `mariadb:11` images with
  a realistic misconfiguration, not a mock. `COPY FROM PROGRAM` really runs a
  shell; `LOAD_FILE` really reads the host file — these are the exact findings a
  real audit flags.
- **C4** is a real OpenSSH daemon; the exploit is a genuine key-based login with
  the leaked key.
- **C5**'s logs are generated from the real flag at boot (the scoreboard
  base64-encodes it and splits it across the attacker session's exfil queries),
  so the forensic path is self-consistent and `make check`-able.

## The forensic challenge

C5 is the "blend" element and the only non-exploitation one. It forces real
correlation rather than a grep:

- The SSH log is mostly brute-force **noise**; exactly one `Accepted publickey`
  is the breach, and it ties back to C4 (the leaked key).
- The DB log has benign sessions, a **decoy** nightly-backup session that *also*
  uses `COPY ... TO PROGRAM`, and the attacker session. Only the attacker
  session's `start` timestamp correlates (within a minute) with the SSH login,
  so a solver that just "decodes all base64" gets the decoy wrong. The reference
  solver correlates by time; a human correlates breach → session → exfil.

## Credentials & the leaked key

All intentional weaknesses are documented in [FLAGS.md](FLAGS.md). The leaked
keypair is committed (private half under `services/webapp/backup/`, public half
as `services/ssh/authorized_keys`) so the two containers agree; regenerate both
together to rotate. `dbadmin` is given a password only to unlock the account for
pubkey login (Alpine locks password-less accounts, which sshd then refuses);
password auth itself is disabled in `sshd_config`.

## Organizer knobs

- Ports: `PG_PORT` (55432), `MY_PORT` (33306), `APP_PORT` (8096), `SSH_PORT`
  (2222), `SB_PORT` (8505).
- Flag strings live in each service (the planted `/flag`, the SQLite row) and in
  [../services/scoreboard/app.py](../services/scoreboard/app.py) for submission
  and for generating C5's logs.

## Self-check

`make check` builds the solver image and runs every exploit in a throwaway
container on the network, submitting each flag. Clean result: **ALL 5 FLAGS
CAPTURED, exit 0.** (The DB daemons take a few seconds to accept connections on a
cold `make up`; the solver retries.)
