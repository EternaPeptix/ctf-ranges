"""c03 — CVE-2026-85608 : Douyin/TikTok Download API unauth SSRF via `url`
(no host/IP allowlist). Flag lives on a loopback-only metadata service."""
import threading, urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from flask import Flask, request, jsonify

FLAG = "FLAG{tiktok_api_ssrf_t0_metadata}"

class Meta(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers()
        self.wfile.write(("instance-identity\nrole: downloader\nflag: " + FLAG + "\n").encode())
    def log_message(self, *a): pass

threading.Thread(target=lambda: HTTPServer(("127.0.0.1", 9999), Meta).serve_forever(),
                 daemon=True).start()

app = Flask(__name__)

@app.get("/")
def home():
    return jsonify(service="TikTok Download API",
                   try_="/api/download?url=https://example.com/video.mp4")

@app.get("/api/download")
@app.get("/api/hybrid/video_data")
def download():
    url = request.args.get("url")
    if not url:
        return jsonify(error="url required"), 400
    try:                                          # no allowlist -> SSRF
        body = urllib.request.urlopen(url, timeout=3).read(2048).decode("latin1")
    except Exception as e:
        return jsonify(error=str(e), url=url), 502
    return jsonify(url=url, data=body)
