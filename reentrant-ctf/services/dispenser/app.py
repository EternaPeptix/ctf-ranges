#!/usr/bin/env python3
"""
Reentrant — dispenser + scoreboard.

Holds the six flags and releases each one ONLY when its challenge is actually
solved on-chain: it verifies by calling the challenge's `isSolved()` via a raw
`eth_call` (selector 0x64d98f6e) against the anvil chain — no web3 dependency.
Setup addresses are read from /shared/addrs.env (written by the deployer).
"""
import json, os, urllib.request
from flask import Flask, request, jsonify, Response

RPC_URL = os.environ.get("RPC_URL", "http://chain:8545")
RPC_PORT = os.environ.get("RPC_PORT", "8545")
IS_SOLVED_SELECTOR = "0x64d98f6e"   # keccak256("isSolved()")[:4]

# (num, name, vuln, real-world echo, addrs.env key, flag)
CH = [
    (1, "The Vault", "Reentrancy", "The DAO (2016)", "C1_SETUP",
     "RKT{r33ntr4ncy_c31_v10l4t10n_dr41n_th3_v4ult}"),
    (2, "The Oracle", "Spot-price oracle manipulation", "bZx / Harvest / Mango", "C2_SETUP",
     "RKT{sp0t_pr1c3_0r4cl3_fl4shl04n_m4n1pul4t10n}"),
    (3, "The Admin", "Unprotected initializer / access control", "Parity init, Rubixi", "C3_SETUP",
     "RKT{unpr0t3ct3d_1n1t_m1ss1ng_4cc3ss_c0ntr0l}"),
    (4, "The Permit", "Signature replay (no nonce)", "permit / meta-tx replay", "C4_SETUP",
     "RKT{s1gn4tur3_r3pl4y_n0_n0nc3_n0_d34dl1n3}"),
    (5, "The Upgrade", "Proxy storage collision", "Parity multisig (2017)", "C5_SETUP",
     "RKT{pr0xy_st0r4g3_c0ll1s10n_d3l3g4t3c4ll_pwn}"),
    (6, "The Shares", "ERC-4626 first-depositor inflation", "ERC-4626 inflation", "C6_SETUP",
     "RKT{3rc4626_f1rst_d3p0s1t0r_sh4r3_1nfl4t10n}"),
]
FLAGS = {c[5]: c[0] for c in CH}
app = Flask(__name__)


def load_addrs():
    out = {}
    try:
        with open("/shared/addrs.env") as f:
            for line in f:
                line = line.strip()
                if "=" in line:
                    k, v = line.split("=", 1)
                    out[k] = v
    except Exception:
        pass
    return out


def rpc(method, params):
    data = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(RPC_URL, data=data, headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=8).read())


def is_solved(setup):
    if not setup:
        return False
    try:
        r = rpc("eth_call", [{"to": setup, "data": IS_SOLVED_SELECTOR}, "latest"])
        res = r.get("result", "0x")
        return int(res, 16) == 1
    except Exception:
        return False


def status():
    a = load_addrs()
    rows = []
    for (n, name, vuln, echo, key, flag) in CH:
        setup = a.get(key)
        solved = is_solved(setup)
        rows.append({"id": n, "name": name, "vuln": vuln, "echo": echo,
                     "setup": setup, "solved": solved,
                     "flag": flag if solved else None})
    return rows


@app.get("/health")
def health():
    return jsonify(ok=True, service="dispenser", rpc=RPC_URL)


@app.get("/result")
def result():
    rows = status()
    return jsonify(challenges=rows, all_solved=all(r["solved"] for r in rows) and len(rows) == 6)


@app.get("/challenges")
def challenges():
    a = load_addrs()
    return jsonify({c[4]: a.get(c[4]) for c in CH})


@app.post("/submit")
def submit():
    flag = (request.get_json(silent=True) or {}).get("flag", "").strip()
    return jsonify(correct=flag in FLAGS, num=FLAGS.get(flag))


PAGE = """<!doctype html><meta charset=utf-8><title>Reentrant</title>
<style>
 body{{font:15px -apple-system,Segoe UI,Arial;max-width:960px;margin:34px auto;padding:0 18px;background:#0b0f14;color:#e4ebf2}}
 h1{{margin:0;color:#64e3a1}} .sub{{color:#8a97a6;margin:4px 0 16px}}
 table{{border-collapse:collapse;width:100%}} td,th{{border-bottom:1px solid #1b2733;padding:9px 10px;text-align:left;font-size:14px}}
 th{{color:#8a97a6;font-weight:600}} .t{{font-weight:600;color:#eef4fa}} code{{background:#14202b;padding:1px 5px;border-radius:4px;color:#8fd6ff;font-size:12px}}
 .ok{{color:#64e3a1;font-weight:700}} .no{{color:#6b7684}} a{{color:#64e3a1;text-decoration:none}}
 .bar{{background:#111a22;border:1px solid #1b2733;border-radius:8px;padding:10px 14px;margin:0 0 16px;color:#aeb9c6;font-size:13px}}
</style>
<h1>⟲ Reentrant</h1>
<p class="sub">A DeFi protocol, thoroughly <b>rekt</b>. Six independent smart-contract challenges on a
local chain — each flag <code>RKT{{...}}</code> is released only when the challenge is solved on-chain.</p>
<div class="bar">Chain RPC: <code>http://localhost:{rpc_port}</code> &nbsp;(chain-id 31337) &middot;
 attacker key = anvil account[1] &middot; attack the contracts directly with <code>cast</code> / <code>forge</code>.
 Each row's <code>isSolved()</code> is checked live.</div>
<table><tr><th>#</th><th>Challenge</th><th>Vulnerability</th><th>Setup contract</th><th>Status</th></tr>
{rows}
</table>
<script>
async function refresh(){{
 let r=await fetch('/result'); let j=await r.json();
 for(const c of j.challenges){{
   let el=document.getElementById('s'+c.id);
   if(el) el.innerHTML = c.solved ? '<span class=ok>✓ solved</span>' : '<span class=no>— unsolved</span>';
 }}
}}
refresh(); setInterval(refresh, 4000);
</script>"""


@app.get("/")
def board():
    a = load_addrs()
    rows = "\n".join(
        f'<tr><td>{n}</td><td class="t">{name}</td><td>{vuln}</td>'
        f'<td><code>{a.get(key) or "deploying…"}</code></td>'
        f'<td id="s{n}">…</td></tr>'
        for (n, name, vuln, echo, key, _f) in CH)
    return Response(PAGE.format(rows=rows, rpc_port=RPC_PORT), mimetype="text/html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, threaded=True)
