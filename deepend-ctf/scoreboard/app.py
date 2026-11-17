#!/usr/bin/env python3
"""The Deep End — scoreboard. Lists the 6 challenges and checks submitted flags."""
from flask import Flask, request, jsonify, Response

# (num, port, technique, cve, product, flag)
CH = [
    (1, 8401, "Proxy routing↔forwarding desync", "CVE-2026-88009",  "Traefik",             "0DAY{traefik_url_0paque_r0ut1ng_d3sync}"),
    (2, 8402, "Auth-protocol canonicalization diff", "CVE-2026-117691", "Keycloak",            "0DAY{saml_r3d1r3ct_p3rc3nt_nam3_c4n0n_d1ff}"),
    (3, 8403, "Adaptor-signature forgery",           "CVE-2026-55174",  "UltrafastSecp256k1",  "0DAY{3cdsa_4dapt0r_pr3s1g_unb0und_t0_T}"),
    (4, 8404, "GF(2¹²⁸) tag forgery", "CVE-2026-81020",  "wolfEngine",          "0DAY{aes_gcm_f0rb1dd3n_4ttack_r3c0v3r_H}"),
    (5, 8405, "Sandbox escape via Formatter",        "CVE-2026-76825",  "RestrictedPython",    "0DAY{r3str1ct3dpy_f0rmatt3r_gl0bals_3scap3}"),
    (6, 8406, "File-format parser differential",     "CVE-2026-115905", "Rust zip2",           "0DAY{z1p2_cl04k1ng_c3ntral_vs_l0cal_h34d3r}"),
]
FLAGS = {c[5]: c[0] for c in CH}
app = Flask(__name__)

PAGE = """<!doctype html><meta charset=utf-8><title>The Deep End</title>
<style>
 body{{font:15px -apple-system,Segoe UI,Arial;max-width:860px;margin:36px auto;padding:0 18px;color:#0e1726;background:#0b0f17}}
 body{{color:#dfe6f0}} h1{{margin:0;color:#6ea8fe}} .sub{{color:#8a94a6;margin:4px 0 20px}}
 table{{border-collapse:collapse;width:100%}} td,th{{border-bottom:1px solid #1e2a3d;padding:9px 10px;text-align:left;font-size:14px}}
 th{{color:#8a94a6;font-weight:600}} .t{{font-weight:600;color:#e8eef7}} code{{background:#16202e;padding:1px 5px;border-radius:4px;color:#9fd0ff}}
 a{{color:#6ea8fe;text-decoration:none}} input{{padding:8px;width:360px;background:#111826;border:1px solid #243247;color:#dfe6f0;border-radius:6px}}
 button{{padding:8px 14px;background:#2447d6;color:#fff;border:0;border-radius:6px}} #m{{margin-left:10px;font-weight:600}}
</style>
<h1>◈ The Deep End</h1>
<p class="sub">Six H2-2026 CVEs where the exploitation <em>technique</em> is the whole puzzle. Submit <code>0DAY{{...}}</code>.</p>
<form onsubmit="s(event)"><input id=f placeholder="0DAY{{...}}" autocomplete=off><button>Submit</button><span id=m></span></form><p></p>
<table><tr><th>#</th><th>Technique</th><th>CVE</th><th>Product</th><th>Target</th></tr>
{rows}
</table>
<script>
async function s(e){{e.preventDefault();let v=document.getElementById('f').value.trim();
 let r=await fetch('/submit',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{flag:v}})}});
 let j=await r.json();let m=document.getElementById('m');
 m.textContent=j.correct?('✓ solved challenge '+j.num):'✗ nope';m.style.color=j.correct?'#5fd38d':'#ff6b6b';}}
</script>"""

@app.get("/")
def board():
    host = (request.host or "localhost").split(":")[0]
    rows = "\n".join(
        f'<tr><td>{n}</td><td class="t">{tech}</td><td><code>{cve}</code></td><td>{prod}</td>'
        f'<td><a href="http://{host}:{port}/" target=_blank>:{port}</a></td></tr>'
        for (n, port, tech, cve, prod, _f) in CH)
    return Response(PAGE.format(rows=rows), mimetype="text/html")

@app.post("/submit")
def submit():
    flag = (request.get_json(silent=True) or {}).get("flag", "").strip()
    num = FLAGS.get(flag)
    return jsonify(correct=num is not None, num=num)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, threaded=True)
