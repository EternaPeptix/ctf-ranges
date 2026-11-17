"""c14 — CVE-2026-102697 : Ollama agent tool approval is prefix-based, but the
full command is run in a shell -> append `; cat /flag` to an approved prefix."""
import subprocess
from flask import Flask, request, jsonify

FLAG = "FLAG{ollama_pr3f1x_appr0val_byp4ss}"    # written to /flag by serve.py
ALLOWED = ("ls", "cat README", "echo", "pwd")   # approved command prefixes
app = Flask(__name__)

@app.get("/")
def home():
    return jsonify(service="Ollama agent runner",
                   hint='POST /api/tool/run {"command":"ls"} ; only approved prefixes run')

@app.post("/api/tool/run")
def run_tool():
    cmd = (request.get_json(force=True, silent=True) or {}).get("command", "")
    if not any(cmd.startswith(p) for p in ALLOWED):     # approval by prefix only
        return jsonify(error="command not approved"), 403
    out = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5).stdout
    return jsonify(command=cmd, output=out)             # ...but the whole string hits the shell
