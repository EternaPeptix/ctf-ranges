#!/usr/bin/env python3
"""Teardown — scoreboard. Lists the 5 pwnables and verifies submitted flags."""
from flask import Flask, request, jsonify, Response

CH = [
    (1, "The Overflow", "ret2win — stack buffer overflow", "9001",
     "TD{r3t2w1n_st4ck_sm4sh_cl4ss1c_0v3rfl0w}"),
    (2, "The Mirror", "format-string arbitrary write (%n)", "9002",
     "TD{f0rmat_str1ng_arb1trary_wr1t3_n_sp3c}"),
    (3, "The Return", "ROP chain: pop rdi -> system('/bin/sh')", "9003",
     "TD{r3t2l1bc_r0p_l34k_g0t_c4ll_syst3m}"),
    (4, "The Lock", "reverse-engineering crackme", "9004",
     "TD{r3v3rs3_th3_s3r14l_x0r_tr4nsf0rm_cr4ckm3}"),
    (5, "The Freelist", "heap UAF → tcache poison → RCE", "9005",
     "TD{h34p_uaf_tc4ch3_p01s0n_fptr_0v3rwr1t3}"),
]
FLAGS = {c[4]: c[0] for c in CH}
app = Flask(__name__)

PAGE = """<!doctype html><meta charset=utf-8><title>Teardown</title>
<style>
 body{{font:15px -apple-system,Segoe UI,Arial;max-width:900px;margin:34px auto;padding:0 18px;background:#0c0c0c;color:#d8d8d2}}
 h1{{margin:0;color:#e0b341}} .sub{{color:#8a8a80;margin:4px 0 16px}}
 table{{border-collapse:collapse;width:100%}} td,th{{border-bottom:1px solid #262620;padding:9px 10px;text-align:left;font-size:14px}}
 th{{color:#8a8a80;font-weight:600}} .t{{font-weight:600;color:#f0f0e8}} code{{background:#1c1c16;padding:1px 5px;border-radius:4px;color:#e0b341;font-size:12px}}
 input{{padding:8px;width:380px;background:#141410;border:1px solid #2a2a22;color:#d8d8d2;border-radius:6px}}
 button{{padding:8px 14px;background:#8a6a1a;color:#fff;border:0;border-radius:6px;cursor:pointer}} #m{{margin-left:10px;font-weight:600}}
</style>
<h1>⌁ Teardown</h1>
<p class="sub">Binary exploitation &amp; reverse engineering. Five pwnables on <code>nc localhost 9001..9005</code>
(glibc 2.31, x86-64). Pop each one for a flag <code>TD{{...}}</code>.</p>
<form onsubmit="s(event)"><input id=f placeholder="TD{{...}}" autocomplete=off><button>Submit</button><span id=m></span></form><p></p>
<table><tr><th>#</th><th>Challenge</th><th>Technique</th><th>Port</th></tr>
{rows}
</table>
<script>
async function s(e){{e.preventDefault();let v=document.getElementById('f').value.trim();
 let r=await fetch('/submit',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{flag:v}})}});
 let j=await r.json();let m=document.getElementById('m');
 m.textContent=j.correct?('✓ pwned '+j.num):'✗ nope';m.style.color=j.correct?'#8ad36a':'#ff6b6b';}}
</script>"""


@app.post("/submit")
def submit():
    flag = (request.get_json(silent=True) or {}).get("flag", "").strip()
    return jsonify(correct=flag in FLAGS, num=FLAGS.get(flag))


@app.get("/")
def board():
    rows = "\n".join(
        f'<tr><td>{n}</td><td class="t">{name}</td><td>{tech}</td><td><code>{port}</code></td></tr>'
        for (n, name, tech, port, _f) in CH)
    return Response(PAGE.format(rows=rows), mimetype="text/html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, threaded=True)
