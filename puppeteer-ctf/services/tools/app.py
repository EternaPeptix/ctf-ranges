#!/usr/bin/env python3
"""
Puppeteer / tools — CVE-2026-40933 (Flowise Custom-MCP stdio command injection).

Flowise lets you register a "Custom MCP" tool by giving a command and its args;
the server launches the stdio MCP process from that config. The flaw: the args
are joined into a shell command line and run through a shell, so an arg carrying
shell metacharacters injects commands on the tool host.

Here the agent invokes a configured MCP tool via POST /mcp/invoke (bearer token
required — the token leaks from the gateway SSRF in stage 2). A directive whose
args contain `; cat /flag` runs arbitrary commands as the tool user.

Isolated training range. Do not deploy.
"""
import subprocess
from flask import Flask, request, jsonify

TOOLS_MCP_TOKEN = "mcp-k3y-9f2c7a1b4e8d"   # must match the gateway's mirror
app = Flask(__name__)


@app.get("/health")
def health():
    return jsonify(ok=True, service="tools")


@app.post("/mcp/invoke")
def invoke():
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {TOOLS_MCP_TOKEN}":
        return jsonify(error="missing/invalid MCP bearer token"), 401

    body = request.get_json(silent=True) or {}
    command = body.get("command", "")
    args = body.get("args", []) or []
    if not isinstance(args, list):
        args = [str(args)]

    # *** The vuln ***: the stdio tool command line is assembled and run through
    # a shell, so metacharacters in args are interpreted.
    cmdline = command + " " + " ".join(str(a) for a in args)
    try:
        p = subprocess.run(cmdline, shell=True, capture_output=True,
                           text=True, timeout=8)
        return jsonify(ok=True, cmdline=cmdline,
                       stdout=p.stdout, stderr=p.stderr, rc=p.returncode)
    except Exception as e:
        return jsonify(ok=False, error=f"{type(e).__name__}: {e}"), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, threaded=True)
