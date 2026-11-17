#!/usr/bin/env python3
"""
C3 — "The Catalog": a tiny storefront backed by SQLite. The product lookup
concatenates the `id` parameter straight into the SQL, so a UNION injection
dumps any table — including the secrets vault. (And the ops "backup" directory
is world-readable: it still has a developer's SSH private key, which is C4.)

Isolated training range. Do not deploy.
"""
import os, sqlite3
from flask import Flask, request, jsonify, send_file, Response

DB = "/tmp/shop.db"
FLAG3 = "AUD{sql1t3_un10n_1nj3ct10n_sql1t3_m4st3r_dump}"

app = Flask(__name__)


def init_db():
    if os.path.exists(DB):
        os.remove(DB)
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE products(id INTEGER, name TEXT, price TEXT)")
    c.executemany("INSERT INTO products VALUES(?,?,?)",
                  [(1, "Widget", "9.99"), (2, "Gadget", "19.99"), (3, "Sprocket", "4.50")])
    # the 'hidden' table a player finds by dumping sqlite_master
    c.execute("CREATE TABLE ops_secret_vault(id INTEGER, k TEXT, v TEXT)")
    c.execute("INSERT INTO ops_secret_vault VALUES(1, 'flag', ?)", (FLAG3,))
    c.commit()
    c.close()


init_db()


@app.get("/")
def home():
    return Response(PAGE, mimetype="text/html")


@app.get("/api/product")
def product():
    pid = request.args.get("id", "1")
    q = "SELECT id, name, price FROM products WHERE id = " + pid   # *** SQL injection ***
    try:
        c = sqlite3.connect(DB)
        rows = c.execute(q).fetchall()
        c.close()
        return jsonify(query=q, rows=rows)
    except Exception as e:
        return jsonify(error=str(e), query=q), 400


@app.get("/backup/<path:f>")
def backup(f):
    # the ops backup directory, left world-readable (an audit finding)
    p = os.path.join("/backup", os.path.basename(f))
    if os.path.isfile(p):
        return send_file(p, mimetype="application/octet-stream")
    return ("not found", 404)


PAGE = """<!doctype html><meta charset=utf-8><title>Sprockets Inc.</title>
<style>body{font:15px -apple-system,Segoe UI,Arial;max-width:720px;margin:36px auto;padding:0 18px;color:#20303f}
code{background:#eef2f6;padding:1px 5px;border-radius:4px}</style>
<h1>🛠 Sprockets Inc.</h1>
<p>Our catalog API: <code>/api/product?id=1</code></p>
<p class=muted>Ops note: nightly backups are in <code>/backup/</code> (TODO: lock this down).</p>
"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, threaded=True)
