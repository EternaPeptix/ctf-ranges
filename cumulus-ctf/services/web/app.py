#!/usr/bin/env python3
"""
Cumulus / web — "CloudSnap", a public image-preview app. Its /fetch endpoint
pulls an arbitrary URL with no allow-list: a textbook SSRF. From the internet
you can only reach this box, but /fetch runs *inside* the cloud network, so it
can hit the internal instance metadata service (imds) and beyond.

Isolated training range. Do not deploy.
"""
import requests
from flask import Flask, request, Response

app = Flask(__name__)


@app.get("/fetch")
def fetch():
    url = request.args.get("url", "")
    if not url:
        return ("usage: /fetch?url=<url>", 400)
    try:
        r = requests.get(url, timeout=6)          # *** SSRF: no validation ***
        return Response(r.content, status=r.status_code,
                        content_type=r.headers.get("Content-Type", "text/plain"))
    except Exception as e:
        return (f"fetch error: {type(e).__name__}: {e}", 502)


PAGE = """<!doctype html><meta charset=utf-8><title>CloudSnap</title>
<style>body{font:15px -apple-system,Segoe UI,Arial;max-width:680px;margin:40px auto;padding:0 18px;color:#1f2a37}
code{background:#eef2f7;padding:1px 5px;border-radius:4px}</style>
<h1>☁ CloudSnap</h1>
<p>Preview any image by URL: <code>/fetch?url=https://example.com/cat.png</code></p>
<p class=muted>Running on cumulus-web-instance.</p>
"""


@app.get("/")
def home():
    return Response(PAGE, mimetype="text/html")


@app.get("/health")
def health():
    return ("ok", 200)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, threaded=True)
