"""c15 — CVE-2026-75854 : ArcadeDB Redis-wire plugin accepts commands with NO
AUTH gate. Minimal RESP server (raw TCP) that serves the flag unauthenticated."""
import socket, threading

FLAG = "FLAG{arcadedb_resp_m1ss1ng_auth}"
STORE = {"flag": FLAG, "greeting": "ArcadeDB RESP plugin"}


def parse(buf: bytes):
    """Return (command_tokens, bytes_consumed) for one RESP array or inline line, or (None,0)."""
    if not buf:
        return None, 0
    if buf[:1] == b"*":                      # RESP array of bulk strings
        try:
            nl = buf.index(b"\r\n"); n = int(buf[1:nl]); i = nl + 2; toks = []
            for _ in range(n):
                assert buf[i:i+1] == b"$"
                nl2 = buf.index(b"\r\n", i); ln = int(buf[i+1:nl2]); i = nl2 + 2
                toks.append(buf[i:i+ln].decode("latin1")); i += ln + 2
            return toks, i
        except Exception:
            return None, 0
    if b"\n" in buf:                          # inline command
        line, _, _ = buf.partition(b"\n")
        return line.decode("latin1").strip().split(), len(line) + 1
    return None, 0


def handle(conn):
    buf = b""
    try:
        while True:
            d = conn.recv(4096)
            if not d:
                break
            buf += d
            while True:
                toks, used = parse(buf)
                if not toks:
                    break
                buf = buf[used:]
                cmd = toks[0].upper()
                if cmd == "PING":
                    conn.sendall(b"+PONG\r\n")
                elif cmd == "GET" and len(toks) > 1:     # no AUTH required (the bug)
                    v = STORE.get(toks[1])
                    conn.sendall(("$%d\r\n%s\r\n" % (len(v), v)).encode() if v is not None
                                 else b"$-1\r\n")
                elif cmd in ("QUIT",):
                    return
                else:
                    conn.sendall(b"-ERR unknown command\r\n")
    except OSError:
        pass
    finally:
        try: conn.close()
        except OSError: pass


def run():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", 80)); s.listen(64)
    print("[c15] ArcadeDB RESP on :80 (no auth)", flush=True)
    while True:
        conn, _ = s.accept()
        threading.Thread(target=handle, args=(conn,), daemon=True).start()
