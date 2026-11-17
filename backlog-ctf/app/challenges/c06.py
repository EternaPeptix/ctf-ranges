"""c06 — CVE-2026-61459 : mcp-server-kubernetes argument injection.
A leading-'-' name slips past the dangerous-flag guard and injects `--server`
into kubectl, which the stub kubectl then uses to exfil the mounted SA token."""
import os, subprocess
from flask import Flask, request, jsonify

FLAG = "FLAG{mcp_k8s_dash_server_arg_1nj}"

# the service-account token (the prize) and a stub kubectl that leaks it when
# an attacker-supplied --server is present
TOK_DIR = "/var/run/secrets/kubernetes.io/serviceaccount"
os.makedirs(TOK_DIR, exist_ok=True)
open(TOK_DIR + "/token", "w").write(FLAG + "\n")
STUB = r'''#!/usr/bin/env python3
import sys
server = next((a for a in sys.argv[1:] if a.startswith("--server")), None)
if server:
    tok = open("/var/run/secrets/kubernetes.io/serviceaccount/token").read().strip()
    print("* redirected to", server.split("=", 1)[-1])
    print("Authorization: Bearer", tok)
else:
    print("NAME    READY   STATUS")
    print("web-0   1/1     Running")
'''
open("/usr/local/bin/kubectl", "w").write(STUB)
os.chmod("/usr/local/bin/kubectl", 0o755)

DANGEROUS = ("--kubeconfig", "--token", "--as", "--insecure")   # incomplete block-list

def guard_ok(arg):
    return not any(arg.startswith(d) for d in DANGEROUS)        # misses --server !

app = Flask(__name__)

@app.get("/")
def home():
    return jsonify(service="mcp-server-kubernetes",
                   try_='POST /tools/get {"resourceType":"pods","name":"web-0"}')

@app.post("/tools/get")
def tools_get():
    b = request.get_json(force=True, silent=True) or {}
    rtype, name = b.get("resourceType", "pods"), b.get("name", "")
    argv = ["kubectl", "get", rtype]              # no `--` separator (bug)
    if name:
        argv.append(name)
    if not all(guard_ok(a) for a in argv):
        return jsonify(error="dangerous flag blocked"), 400
    out = subprocess.run(argv, capture_output=True, text=True, timeout=5).stdout
    return jsonify(cmd=" ".join(argv), output=out)
