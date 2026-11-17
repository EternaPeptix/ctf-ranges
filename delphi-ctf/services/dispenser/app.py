#!/usr/bin/env python3
"""
Delphi — dispenser + scoreboard.

Holds the six flags and releases each one ONLY when its challenge is actually
solved on-chain: it verifies by calling the challenge's `isSolved()` via a raw
`eth_call` (selector 0x64d98f6e) against the anvil chain — no web3 dependency.
Setup addresses are read from /shared/addrs.env (written by the deployer).
"""
import json, os, urllib.request
from flask import Flask, request, jsonify, Response

RPC_URL = os.environ.get("RPC_URL", "http://chain:8545")
RPC_PORT = os.environ.get("RPC_PORT", "8547")
IS_SOLVED_SELECTOR = "0x64d98f6e"   # keccak256("isSolved()")[:4]

# (num, name, flaw, real-world echo, addrs.env key, flag)
CH = [
    (1, "The Floor", "Chainlink minAnswer clamp", "Venus / Blizz on LUNA", "C1_SETUP",
     "ORC{m1n4nsw3r_cl4mp_lun4_fl00r_pr1c3_r3ad}"),
    (2, "The Stale", "Missing freshness check", "assorted staleness hacks", "C2_SETUP",
     "ORC{st4l3_f33d_n0_fr3shn3ss_ch3ck_h34rtb34t}"),
    (3, "The Window", "Short-window TWAP manipulation", "Inverse Finance", "C3_SETUP",
     "ORC{tw4p_sh0rt_w1nd0w_t1m3_w31ght3d_m4n1p}"),
    (4, "The Mirror", "Read-only reentrancy on LP price", "Curve read-only reentrancy", "C4_SETUP",
     "ORC{r34d_0nly_r33ntr4ncy_v1rtu4l_pr1c3}"),
    (5, "The Mint", "Naive LP-token spot pricing", "Warp Finance / Cheese Bank", "C5_SETUP",
     "ORC{n41v3_lp_t0k3n_sp0t_r3s3rv3_pr1c1ng}"),
    (6, "The Scale", "Oracle decimals / scaling confusion", "oracle-integration bugs", "C6_SETUP",
     "ORC{0r4cl3_d3c1m4ls_sc4l1ng_c0nfus10n_1e10}"),
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
        return int(r.get("result", "0x"), 16) == 1
    except Exception:
        return False


def status():
    a = load_addrs()
    rows = []
    for (n, name, flaw, echo, key, flag) in CH:
        setup = a.get(key)
        solved = is_solved(setup)
        rows.append({"id": n, "name": name, "flaw": flaw, "echo": echo,
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


PAGE = """<!doctype html><meta charset=utf-8><title>Delphi</title>
<style>
 body{{font:15px -apple-system,Segoe UI,Arial;max-width:980px;margin:34px auto;padding:0 18px;background:#0c0a14;color:#e9e4f2}}
 h1{{margin:0;color:#c9a6ff}} .sub{{color:#9a90aa;margin:4px 0 16px}}
 table{{border-collapse:collapse;width:100%}} td,th{{border-bottom:1px solid #241d33;padding:9px 10px;text-align:left;font-size:14px}}
 th{{color:#9a90aa;font-weight:600}} .t{{font-weight:600;color:#f3eefb}} code{{background:#1b1430;padding:1px 5px;border-radius:4px;color:#d2b3ff;font-size:12px}}
 .ok{{color:#8ef0b0;font-weight:700}} .no{{color:#6b6480}} a{{color:#c9a6ff;text-decoration:none}}
 .bar{{background:#140f24;border:1px solid #241d33;border-radius:8px;padding:10px 14px;margin:0 0 16px;color:#bdb3cc;font-size:13px}}
</style>
<h1>⟐ Delphi</h1>
<p class="sub">Every challenge is a different way that trusting a price goes wrong. Six independent
smart-contract challenges on a local chain — each flag <code>ORC{{...}}</code> is released only when
the challenge is solved on-chain.</p>
<div class="bar">Chain RPC: <code>http://localhost:{rpc_port}</code> (chain-id 31337) &middot;
 attacker = anvil account[1] &middot; attack the contracts with <code>cast</code> / <code>forge</code>.
 Each row's <code>isSolved()</code> is polled live.</div>
<table><tr><th>#</th><th>Challenge</th><th>Oracle flaw</th><th>Setup contract</th><th>Status</th></tr>
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
        f'<tr><td>{n}</td><td class="t">{name}</td><td>{flaw}</td>'
        f'<td><code>{a.get(key) or "deploying…"}</code></td>'
        f'<td id="s{n}">…</td></tr>'
        for (n, name, flaw, echo, key, _f) in CH)
    return Response(PAGE.format(rows=rows, rpc_port=RPC_PORT), mimetype="text/html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, threaded=True)
