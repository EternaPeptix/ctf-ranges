#!/usr/bin/env python3
"""
The Gauntlet — dispenser + scoreboard.

Holds the seven flags and releases each one ONLY when its challenge is actually
solved on-chain: it verifies by calling the challenge's `isSolved()` via a raw
`eth_call` (selector 0x64d98f6e). Setup addresses come from /shared/addrs.env.
"""
import json, os, urllib.request
from flask import Flask, request, jsonify, Response

RPC_URL = os.environ.get("RPC_URL", "http://chain:8545")
RPC_PORT = os.environ.get("RPC_PORT", "8549")
IS_SOLVED_SELECTOR = "0x64d98f6e"

# (num, name, technique, echo, addrs.env key, flag)
CH = [
    (1, "The Signet", "ECDSA nonce reuse → key recovery", "Sony PS3 / biased nonces", "C1_SETUP",
     "GG{3cdsa_n0nc3_r3us3_pr1v4t3_k3y_r3c0v3ry}"),
    (2, "The Branch", "Merkle second-preimage (leaf/node confusion)", "OpenZeppelin advisory", "C2_SETUP",
     "GG{m3rkl3_s3c0nd_pr31m4g3_l34f_n0d3_c0nfus10n}"),
    (3, "The Phantom", "ecrecover returns address(0)", "classic signature bug", "C3_SETUP",
     "GG{3cr3c0v3r_r3turns_z3r0_f0r_1nv4l1d_s1g}"),
    (4, "The Latch", "EIP-1153 transient-storage reentrancy", "Cancun-era reentrancy", "C4_SETUP",
     "GG{31p1153_tr4ns13nt_cr0ss_funct10n_r33ntr4ncy}"),
    (5, "The Dice", "Weak randomness (prevrandao)", "Fomo3D / lottery hacks", "C5_SETUP",
     "GG{pr3vr4nd40_w34k_r4nd0mn3ss_s4m3_bl0ck}"),
    (6, "The Clash", "Selector/facet delegatecall hijack", "Diamond / proxy misconfig", "C6_SETUP",
     "GG{s3l3ct0r_f4c3t_h1j4ck_d3l3g4t3c4ll_r0ut3r}"),
    (7, "The Keystone", "BN254 pairing-verifier bypass", "broken ZK verifiers", "C7_SETUP",
     "GG{bn254_p41r1ng_v3r1f13r_z3r0_pr00f_f0rg3ry}"),
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
                    k, v = line.split("=", 1); out[k] = v
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
    return [{"id": n, "name": name, "technique": tech, "echo": echo, "setup": a.get(key),
             "solved": is_solved(a.get(key)),
             "flag": flag if is_solved(a.get(key)) else None}
            for (n, name, tech, echo, key, flag) in CH]


@app.get("/health")
def health():
    return jsonify(ok=True, service="dispenser", rpc=RPC_URL)


@app.get("/result")
def result():
    rows = status()
    return jsonify(challenges=rows, all_solved=all(r["solved"] for r in rows) and len(rows) == 7)


@app.get("/challenges")
def challenges():
    a = load_addrs()
    return jsonify({c[4]: a.get(c[4]) for c in CH})


@app.post("/submit")
def submit():
    flag = (request.get_json(silent=True) or {}).get("flag", "").strip()
    return jsonify(correct=flag in FLAGS, num=FLAGS.get(flag))


PAGE = """<!doctype html><meta charset=utf-8><title>The Gauntlet</title>
<style>
 body{{font:15px -apple-system,Segoe UI,Arial;max-width:1000px;margin:34px auto;padding:0 18px;background:#0a0b10;color:#e7ebf2}}
 h1{{margin:0;color:#ff8f6b}} .sub{{color:#8c93a3;margin:4px 0 16px}}
 table{{border-collapse:collapse;width:100%}} td,th{{border-bottom:1px solid #1f2430;padding:9px 10px;text-align:left;font-size:14px}}
 th{{color:#8c93a3;font-weight:600}} .t{{font-weight:600;color:#f2f5fa}} code{{background:#161c28;padding:1px 5px;border-radius:4px;color:#9fd0ff;font-size:12px}}
 .ok{{color:#6be39b;font-weight:700}} .no{{color:#646c7d}} a{{color:#ff8f6b;text-decoration:none}}
 .bar{{background:#11141d;border:1px solid #1f2430;border-radius:8px;padding:10px 14px;margin:0 0 16px;color:#aab2c0;font-size:13px}}
</style>
<h1>⚔ The Gauntlet</h1>
<p class="sub">The hardest range. Seven research-grade on-chain primitives — ECDSA cryptanalysis, a Merkle
second-preimage, an ecrecover quirk, transient-storage reentrancy, weak randomness, a selector hijack,
and a pairing-verifier forgery. Each flag <code>GG{{...}}</code> is released only on an on-chain solve.</p>
<div class="bar">Chain RPC: <code>http://localhost:{rpc_port}</code> (chain-id 31337, Cancun) &middot;
 attacker = anvil account[1] &middot; drive it with <code>cast</code> / <code>forge</code>. Each
 <code>isSolved()</code> is polled live.</div>
<table><tr><th>#</th><th>Challenge</th><th>Technique</th><th>Setup contract</th><th>Status</th></tr>
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
        f'<tr><td>{n}</td><td class="t">{name}</td><td>{tech}</td>'
        f'<td><code>{a.get(key) or "deploying…"}</code></td>'
        f'<td id="s{n}">…</td></tr>'
        for (n, name, tech, echo, key, _f) in CH)
    return Response(PAGE.format(rows=rows, rpc_port=RPC_PORT), mimetype="text/html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, threaded=True)
