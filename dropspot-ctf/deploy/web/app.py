#!/usr/bin/env python3
"""
Dropspot  —  dropspot.example  ("Share files privately. Probably.")

A deliberately careless web app. Every bug here is blindingly obvious once you
see it and incredibly easy to miss in a hurry:

  * exposed /.git  (secrets live forever in history)                  -> flag 1
  * IDOR: /d/<id> has no owner check, just change the number          -> flag 2
  * mass assignment: /api/register merges your whole JSON, incl. role -> flag 3
  * JWT verify accepts alg:none (unsigned tokens)                     -> flag 4
  * /admin-x9z1/internal trusts X-Forwarded-For for "localhost only"  -> flag 5
  * /api/config?debug=1 dumps secrets (debug left on in prod)         -> flag 6
  * /uploads/backup.zip sitting in the webroot                        -> flag 7 (final)
  * a flag in an HTML comment, and one in a response header           -> bonus

Isolated training range — do not deploy (obviously).
"""
import os, json, base64, hmac, hashlib, zipfile
from flask import Flask, request, jsonify, send_from_directory, Response

app = Flask(__name__)
PUBLIC = os.path.join(os.path.dirname(__file__), "public")

# JWT signing secret — also sitting in the exposed .git history (flag 1).
SECRET = "s3cr3t"

FLAGS = {
    2: "DS{1d0r_jus7_ch4ng3_th3_numb3r_1n_th3_url}",
    3: "DS{m4ss_4ss1gnm3nt_s3t_y0ur_0wn_r0le_4dm1n}",
    4: "DS{jwt_4lg_n0ne_n0_s1gn4tur3_n0_pr0bl3m}",
    5: "DS{x_f0rw4rd3d_f0r_1s_jus7_4_h34d3r_y0u_s3nd}",
    6: "DS{d3bug_m0d3_l3ft_0n_1n_pr0duct10n}",
    7: "DS{backup_z1p_1n_th3_w3br00t_g00gl3_d0rk_1t}",
    "hdr": "DS{y0u_r34d_th3_r3sp0ns3_h34d3rs_n1c3}",
}

# ---- the "nightly backup" someone left in the webroot (flag 7) ------------
os.makedirs(os.path.join(PUBLIC, "uploads"), exist_ok=True)
_bk = os.path.join(PUBLIC, "uploads", "backup.zip")
if not os.path.exists(_bk):
    with zipfile.ZipFile(_bk, "w") as z:
        z.writestr("dropspot_backup/README.txt", "nightly db backup. TODO: move off the webroot.\n")
        z.writestr("dropspot_backup/flag.txt", FLAGS[7] + "\n")
        z.writestr("dropspot_backup/users.sql",
                   "-- users (bcrypt hashes)\n"
                   "INSERT INTO users VALUES (1,'admin','2y10REDACTEDhashdeadbeef','admin');\n")

# ---- in-memory data --------------------------------------------------------
USERS = {"admin": {"username": "admin", "role": "admin"}}
SHARES = {
    1: {"owner": "admin", "name": "board-deck-DO-NOT-SHARE.txt", "private": True,
        "content": ("Q4 board deck notes (CONFIDENTIAL).\n"
                    f"{FLAGS[2]}\n"
                    "ps: the admin console is at /admin-x9z1 (needs role=admin).\n")},
    2: {"owner": "admin", "name": "payroll.csv", "private": True,
        "content": "name,salary\nfounder,1\neveryone else,0\n"},
    1006: {"owner": "guest", "name": "cat.jpg", "private": False, "content": "(a cat)"},
    1007: {"owner": "guest", "name": "memo.txt", "private": False, "content": "lunch is at noon"},
}


# ---- hand-rolled JWT (so alg:none is genuinely accepted — the bug) ---------
def b64u(b): return base64.urlsafe_b64encode(b).rstrip(b"=").decode()
def b64ud(s): return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))

def jwt_encode(payload):
    h = b64u(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    p = b64u(json.dumps(payload).encode())
    sig = b64u(hmac.new(SECRET.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest())
    return f"{h}.{p}.{sig}"

def jwt_decode(token):
    """Returns (payload, alg) or (None, None)."""
    try:
        h, p, s = token.split(".")
        alg = json.loads(b64ud(h)).get("alg", "")
        payload = json.loads(b64ud(p))
        if alg == "none":                       # <-- accepts unsigned tokens
            return payload, "none"
        if alg == "HS256":
            exp = b64u(hmac.new(SECRET.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest())
            if hmac.compare_digest(exp, s):
                return payload, "HS256"
    except Exception:
        pass
    return None, None

def current_token():
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.cookies.get("session", "")


@app.after_request
def add_header(resp):
    # bonus: a flag just sitting in a response header on every response
    resp.headers["X-Powered-By"] = f"Dropspot/1.0 ({FLAGS['hdr']})"
    return resp


# ===========================================================================
@app.route("/")
def home():
    return send_from_directory(PUBLIC, "index.html")

# ---- API: register with mass assignment (flag 3) --------------------------
@app.post("/api/register")
def register():
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username")
    if not username:
        return jsonify(error="username required"), 400
    user = {"username": username, "role": "user"}
    user.update(data)                            # <-- MASS ASSIGNMENT
    USERS[username] = user
    out = {"token": jwt_encode({"username": username, "role": user.get("role", "user")}),
           "role": user.get("role", "user")}
    if user.get("role") == "admin":
        out["flag"] = FLAGS[3]
        out["note"] = "you just set your own role to admin on signup."
    return jsonify(out)

@app.post("/api/login")
def login():
    data = request.get_json(force=True, silent=True) or {}
    u = data.get("username", "guest")
    role = USERS.get(u, {}).get("role", "user")
    return jsonify(token=jwt_encode({"username": u, "role": role}), role=role)

# ---- API: whoami; detects alg:none admin tokens (flag 4) ------------------
@app.get("/api/me")
def me():
    payload, alg = jwt_decode(current_token())
    if payload is None:
        return jsonify(error="invalid or missing token"), 401
    out = {"claims": payload, "alg": alg}
    if alg == "none" and payload.get("role") == "admin":
        out["flag"] = FLAGS[4]
        out["note"] = "that token has no signature (alg=none) and you're still admin."
    return jsonify(out)

# ---- IDOR: no owner check, just change the number (flag 2) -----------------
@app.get("/d/<int:share_id>")
def download(share_id):
    s = SHARES.get(share_id)
    if not s:
        return jsonify(error="no such share"), 404
    return jsonify(id=share_id, owner=s["owner"], name=s["name"], content=s["content"])

# ---- admin console (reach it via flag 3 or flag 4) ------------------------
@app.get("/admin-x9z1")
def admin():
    payload, _ = jwt_decode(current_token())
    if not payload or payload.get("role") != "admin":
        return Response("403 Forbidden — admin console, role=admin required.\n", 403,
                        mimetype="text/plain")
    return Response(
        "Dropspot admin console\n"
        f"welcome, {payload.get('username')}.\n\n"
        "ops endpoints:\n"
        " - /admin-x9z1/internal   (restricted to localhost / 127.0.0.1)\n"
        " - /api/config?debug=1    (diagnostics)\n"
        " - nightly backup lands in /uploads/ (don't forget to move it off the webroot!)\n",
        mimetype="text/plain")

# ---- "localhost only" internal API, trusts X-Forwarded-For (flag 5) -------
@app.get("/admin-x9z1/internal")
def internal():
    xff = request.headers.get("X-Forwarded-For", request.remote_addr or "")
    client = xff.split(",")[0].strip()
    if client != "127.0.0.1":
        return jsonify(error=f"internal API is localhost-only (you are {client})"), 403
    return jsonify(flag=FLAGS[5], db_user="dropspot", db_pass="dropspot",
                   note="backup of the whole db is at /uploads/backup.zip")

# ---- debug config dump (flag 6) -------------------------------------------
@app.get("/api/config")
def config():
    if request.args.get("debug") == "1":
        return jsonify(env="production", debug=True, jwt_secret=SECRET,
                       admin_user="admin", flag=FLAGS[6],
                       backup="/uploads/backup.zip",
                       note="debug=1 should absolutely not be enabled in prod")
    return jsonify(env="production", debug=False)

# ---- catch-all static: serves /robots.txt, /.git/*, /uploads/*, /app.js ---
@app.get("/<path:p>")
def static_files(p):
    try:
        return send_from_directory(PUBLIC, p)
    except Exception:
        return jsonify(error="not found", path=p), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
