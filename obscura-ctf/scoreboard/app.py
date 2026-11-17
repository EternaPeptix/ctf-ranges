#!/usr/bin/env python3
"""Obscura — scoreboard. Lists the 5 widgets and checks submitted flags."""
from flask import Flask, request, jsonify, Response

# (num, port, name, category, tagline, flag)
CH = [
    (1, 8601, "reverb", "Signatures",   "Reproducible Schnorr signatures",      "FLAG{reverb_deterministic_nonces_are_linear_8f3c91}"),
    (2, 8602, "echo",   "Zero-knowledge","Passwordless proof-of-identity",       "FLAG{echo_fiat_shamir_must_bind_the_commitment_a7d20e}"),
    (3, 8603, "warden", "Web / auth",    "HMAC-signed download links",           "FLAG{warden_authorize_then_normalize_is_backwards_5b1e74}"),
    (4, 8604, "tally",  "Symmetric",     "Sealed one-time envelopes",            "FLAG{tally_keystream_keyed_only_by_label_length_d48a06}"),
    (5, 8605, "cage",   "Sandbox / RE",  "Verified formula sandbox (bytecode)",  "FLAG{cage_verifier_scans_linearly_the_vm_jumps_anywhere_c0ffee}"),
]
FLAGS = {c[5]: c[0] for c in CH}
app = Flask(__name__)

PAGE = """<!doctype html><meta charset=utf-8><title>Obscura</title>
<style>
 body{{font:15px -apple-system,Segoe UI,Arial;max-width:860px;margin:36px auto;padding:0 18px;color:#1b1030;background:#fbf9ff}}
 h1{{margin:0;color:#6d28d9}} .sub{{color:#7c7196;margin:4px 0 20px}}
 table{{border-collapse:collapse;width:100%}} td,th{{border-bottom:1px solid #ece6f7;padding:9px 10px;text-align:left;font-size:14px}}
 th{{color:#6a5f84;font-weight:600}} .name{{font-weight:700;color:#5b21b6}} .cat{{color:#7c7196}}
 code{{background:#f0ebfa;padding:1px 5px;border-radius:4px}}
 a{{color:#7c3aed;text-decoration:none}} input{{padding:8px;width:360px}}
 button{{padding:8px 14px;background:#6d28d9;color:#fff;border:0;border-radius:6px}}
 #msg{{margin-left:10px;font-weight:600}}
</style>
<h1>\U0001f52e Obscura</h1>
<p class="sub">Provably secure. Allegedly. Five original widgets, five original flaws —
no CVE, no public PoC. Brutal black-box; a one-liner once you see it. Submit <code>FLAG{{...}}</code>.</p>
<form onsubmit="sub(event)"><input id=f placeholder="FLAG{{...}}" autocomplete=off>
<button>Submit</button><span id=msg></span></form>
<p></p>
<table><tr><th>#</th><th>Widget</th><th>Category</th><th>What it claims to do</th><th>Target</th></tr>
{rows}
</table>
<script>
async function sub(e){{e.preventDefault();let v=document.getElementById('f').value.trim();
 let r=await fetch('/submit',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{flag:v}})}});
 let o=await r.json();let m=document.getElementById('msg');
 m.textContent=o.correct?('✓ correct — widget '+o.num):'✗ not a valid flag';
 m.style.color=o.correct?'#1a7f37':'#b02a37';}}
</script>"""


@app.get("/")
def board():
    host = (request.host or "localhost").split(":")[0]
    rows = "\n".join(
        f'<tr><td>{n}</td><td class="name">{name}</td><td class="cat">{cat}</td>'
        f'<td>{tag}</td><td><a href="http://{host}:{port}/" target=_blank>:{port}</a></td></tr>'
        for (n, port, name, cat, tag, _flag) in CH)
    return Response(PAGE.format(rows=rows), mimetype="text/html")


@app.post("/submit")
def submit():
    flag = (request.get_json(silent=True) or {}).get("flag", "").strip()
    num = FLAGS.get(flag)
    return jsonify(correct=num is not None, num=num)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, threaded=True)
