#!/usr/bin/env python3
"""
Puppeteer / gateway — CVE-2026-110719 (Portkey AI Gateway custom-host SSRF).

The gateway is an LLM-egress proxy. A client picks the upstream provider, and
Portkey lets a request override the upstream host with the header
`x-portkey-custom-host`. The flaw: that host is forwarded with NO validation,
so a request can aim the gateway at `127.0.0.1` (or any internal host) and turn
it into an SSRF primitive.

The gateway also exposes a loopback-only metadata endpoint that mirrors the
provider credentials — reachable ONLY from 127.0.0.1. A steered agent that sets
`x-portkey-custom-host: 127.0.0.1` makes the gateway fetch its own metadata
endpoint over loopback, so the guard passes and the secret leaks.

Isolated training range. Do not deploy.
"""
import requests
from flask import Flask, request, jsonify, Response

FLAG2 = "PUP{portk3y_cust0m_h0st_l00pback_ssrf}"
TOOLS_MCP_TOKEN = "mcp-k3y-9f2c7a1b4e8d"   # the credential the SSRF leaks

app = Flask(__name__)


@app.get("/health")
def health():
    return jsonify(ok=True, service="gateway")


@app.get("/internal/metadata")
def metadata():
    """Loopback-only provider-metadata mirror. Must come from 127.0.0.1."""
    remote = request.remote_addr or ""
    if remote not in ("127.0.0.1", "::1"):
        return jsonify(error="metadata is loopback-only", seen=remote), 403
    return jsonify(
        provider="portkey",
        note="internal provider credential mirror",
        flag=FLAG2,
        tools_mcp_token=TOOLS_MCP_TOKEN,
        tools_endpoint="http://tools/mcp/invoke",
        hint="POST /mcp/invoke with Authorization: Bearer <tools_mcp_token>, body {command,args}",
    )


@app.post("/v1/proxy")
def proxy():
    """
    Forward an LLM/egress call to the upstream provider. If the caller supplies
    `x-portkey-custom-host`, that host overrides the upstream (the vuln: no
    allow-list, no loopback/link-local filtering).
    """
    body = request.get_json(silent=True) or {}
    path = body.get("path", "/")
    custom = request.headers.get("x-portkey-custom-host")

    if not custom:
        # Normal operation: a benign canned provider response (the real upstream
        # is an external LLM API that isn't reachable from this training range).
        return jsonify(provider="default", model="helm-llm-1",
                       choices=[{"text": "(provider response)"}])

    host = custom if "://" in custom else "http://" + custom
    url = host.rstrip("/") + "/" + path.lstrip("/")
    try:
        r = requests.get(url, timeout=8)
        return Response(r.content, status=r.status_code,
                        content_type=r.headers.get("Content-Type", "text/plain"))
    except Exception as e:
        return jsonify(error=f"upstream fetch failed: {type(e).__name__}: {e}",
                       url=url), 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, threaded=True)
