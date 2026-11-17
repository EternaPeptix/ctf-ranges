#!/usr/bin/env python3
"""
Keyhaven edge proxy  —  app.keyhaven.example  (the only published service)

Two jobs:

 1. Reverse proxy to the SSO backend, with the HTTP request-smuggling parser
    differential behind CVE-2019-18277: the edge frames a body by the FIRST
    `Transfer-Encoding` header only if it is exactly `chunked`, else by
    Content-Length, and enforces an ACL (`/internal` => 403). The SSO backend
    frames leniently (any TE containing `chunked`), so an attacker can smuggle a
    request past the ACL.  -> stage 1

 2. An authenticated corp gateway: `/gw/<svc>/<path>` is proxied to the internal
    service `<svc>.corp.keyhaven.example` ONLY when the request carries a valid
    `kh_corp` session cookie (an HMAC the SSO issues after a SAML-admin login).
    This is how a player, having smuggled in and completed SAML, reaches the
    api / vault / signer services.

Isolated training range — do not deploy.
"""
import os, socket, threading, hmac, hashlib

UPSTREAM = (os.getenv("UPSTREAM_HOST", "sso.corp.keyhaven.example"),
            int(os.getenv("UPSTREAM_PORT", "80")))
SECRET = os.getenv("KH_CORP_SECRET", "k3yh4v3n-c0rp-s3cr3t-2026").encode()
CORP_TOKEN = hmac.new(SECRET, b"corp-admin", hashlib.sha256).hexdigest()
GW_HOSTS = {"api": "api.corp.keyhaven.example",
            "vault": "vault.corp.keyhaven.example",
            "signer": "signer.corp.keyhaven.example"}


def recv_head(sock):
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            break
        buf += chunk
        if len(buf) > 65536:
            break
    head, _, rest = buf.partition(b"\r\n\r\n")
    return head, rest

def parse_head(head):
    lines = head.split(b"\r\n")
    rl = lines[0].decode("latin1") if lines else ""
    parts = rl.split(" ")
    method = parts[0] if parts else "GET"
    path = parts[1] if len(parts) > 1 else "/"
    headers = []
    for ln in lines[1:]:
        if b":" in ln:
            n, _, v = ln.partition(b":")
            headers.append((n.decode("latin1").strip(), v.decode("latin1").strip()))
    return method, path, headers

def get_cookie(headers, name):
    for n, v in headers:
        if n.lower() == "cookie":
            for part in v.split(";"):
                k, _, val = part.strip().partition("=")
                if k == name:
                    return val
    return None

def read_exact(sock, pre, n):
    buf = bytearray(pre)
    while len(buf) < n:
        c = sock.recv(min(65536, n - len(buf)))
        if not c:
            break
        buf += c
    return bytes(buf[:n])

def read_chunked_raw(sock, pre):
    buf = bytearray(pre)
    while b"0\r\n\r\n" not in bytes(buf):
        c = sock.recv(4096)
        if not c:
            break
        buf += c
    return bytes(buf)

def send_403(client, msg):
    body = msg.encode()
    client.sendall(b"HTTP/1.1 403 Forbidden\r\nContent-Type: text/plain\r\n"
                   b"Connection: close\r\nContent-Length: " + str(len(body)).encode()
                   + b"\r\n\r\n" + body)

def proxy_to(host, raw, client):
    try:
        up = socket.create_connection((host, 80), timeout=10)
        up.sendall(raw)
        up.settimeout(60)
        while True:
            data = up.recv(65536)
            if not data:
                break
            client.sendall(data)
        up.close()
    except OSError:
        pass


def handle(client):
    client.settimeout(70)
    try:
        head, rest = recv_head(client)
        if not head:
            return
        method, path, headers = parse_head(head)
        clean = path.split("?", 1)[0]

        # read the body per the edge's framing (first-TE-strict, else CL)
        te = [v for (n, v) in headers if n.lower() == "transfer-encoding"]
        cl = [v for (n, v) in headers if n.lower() == "content-length"]
        if te and te[0].strip().lower() == "chunked":
            body = read_chunked_raw(client, rest)
        else:
            n = int(cl[0]) if cl and cl[0].strip().isdigit() else 0
            body = read_exact(client, rest, n)
        raw = head + b"\r\n\r\n" + body

        # ---- authenticated corp gateway --------------------------------------
        if clean.startswith("/gw/"):
            seg = clean[4:].split("/", 1)
            svc = seg[0]
            sub = "/" + (seg[1] if len(seg) > 1 else "")
            if "?" in path:
                sub += "?" + path.split("?", 1)[1]
            if svc not in GW_HOSTS:
                send_403(client, "unknown gateway service\n"); return
            if not hmac.compare_digest(get_cookie(headers, "kh_corp") or "", CORP_TOKEN):
                send_403(client, "corp gateway requires a valid kh_corp session (SAML admin)\n"); return
            # rebuild a clean forward request to the internal service
            fwd_headers = [(n, v) for (n, v) in headers
                           if n.lower() not in ("host", "transfer-encoding")]
            lines = [f"{method} {sub} HTTP/1.1", f"Host: {GW_HOSTS[svc]}", "Connection: close"]
            has_cl = any(n.lower() == "content-length" for n, _ in fwd_headers)
            for n, v in fwd_headers:
                if n.lower() == "connection":
                    continue
                lines.append(f"{n}: {v}")
            if body and not has_cl:
                lines.append(f"Content-Length: {len(body)}")
            fwd = ("\r\n".join(lines) + "\r\n\r\n").encode() + body
            proxy_to(GW_HOSTS[svc], fwd, client)
            return

        # ---- edge ACL: /internal is forbidden (smuggling bypasses it) --------
        if clean.startswith("/internal"):
            send_403(client, "edge: /internal is not accessible\n"); return

        # ---- default: forward verbatim to SSO (keeps the smuggling path) -----
        proxy_to(UPSTREAM[0], raw, client)
    except Exception:
        pass
    finally:
        try:
            client.close()
        except Exception:
            pass


def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", 80)); s.listen(128)
    print("[edge] listening on :80; upstream", UPSTREAM, "; gw services", list(GW_HOSTS), flush=True)
    while True:
        c, _ = s.accept()
        threading.Thread(target=handle, args=(c,), daemon=True).start()

if __name__ == "__main__":
    main()
