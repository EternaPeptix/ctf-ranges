"""c01 — CVE-2026-48528 : NCEAS Metacat unauth SQL injection via nodeId.
Re-impl as UNION-based SQLi over sqlite with query echoed on error."""
import sqlite3, threading
from flask import Flask, request, jsonify

FLAG = "FLAG{metacat_unauth_err0r_sqli}"
_lock = threading.Lock()
_db = sqlite3.connect(":memory:", check_same_thread=False)
_db.executescript("""
CREATE TABLE objects(id TEXT, node_id TEXT, title TEXT);
INSERT INTO objects VALUES ('obj-1','urn:node:KNB','Arctic salmon counts'),
                           ('obj-2','urn:node:ARCTIC','Sea-ice extent 2026');
CREATE TABLE cn_secrets(name TEXT, secret TEXT);
INSERT INTO cn_secrets VALUES ('cn_flag', '%s');
""" % FLAG)

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify(service="Metacat Coordinating Node",
                   try_="/cn/v2/object?nodeId=urn:node:KNB")

@app.route("/cn/v1/object")
@app.route("/cn/v2/object")
def obj():
    node = request.args.get("nodeId", "urn:node:KNB")
    q = "SELECT id, title FROM objects WHERE node_id = '%s'" % node   # <-- injectable
    try:
        with _lock:
            rows = _db.execute(q).fetchall()
        return jsonify(query=q, objectList=[{"identifier": r[0], "title": r[1]} for r in rows])
    except Exception as e:                       # errors echo the query (error-based feel)
        return jsonify(error=str(e), query=q), 500
