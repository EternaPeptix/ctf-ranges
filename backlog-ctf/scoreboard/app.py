#!/usr/bin/env python3
"""The Backlog — scoreboard. Lists the 15 challenges and checks submitted flags."""
from flask import Flask, request, jsonify, Response

# (num, port, category, cve, product, flag)
CH = [
    (1, 8301, "SQL injection",        "CVE-2026-48528",  "NCEAS Metacat",            "FLAG{metacat_unauth_err0r_sqli}"),
    (2, 8302, "SSTI",                 "CVE-2026-96355",  "Drupal Webform",           "FLAG{drupal_webf0rm_twig_sst1}"),
    (3, 8303, "SSRF",                 "CVE-2026-85608",  "TikTok Download API",      "FLAG{tiktok_api_ssrf_t0_metadata}"),
    (4, 8304, "LFI / parser",         "CVE-2026-55554",  "Dompdf",                   "FLAG{dompdf_strp0s_chr00t_byp4ss_lfi}"),
    (5, 8305, "Upload → RCE",    "CVE-2026-72557",  "Cockpit CMS",              "FLAG{cockpit_wildcard_upl0ad_w3bshell}"),
    (6, 8306, "Argument injection",   "CVE-2026-61459",  "mcp-server-kubernetes",    "FLAG{mcp_k8s_dash_server_arg_1nj}"),
    (7, 8307, "XXE",                  "CVE-2026-54640",  "OpenRemote",               "FLAG{openremote_ets_xxe_f1le_r34d}"),
    (8, 8308, "IDOR",                 "CVE-2026-53548",  "Termix",                   "FLAG{termix_id0r_ssh_passw0rd_by_id}"),
    (9, 8309, "JWT auth bypass",      "CVE-2026-54733",  "Moodle local_o365",        "FLAG{moodle_unsigned_jwt_upn_trust}"),
    (10, 8310, "Authz normalization", "CVE-2026-105986", "Kong Gateway",             "FLAG{kong_percent_enc0d3_rbac_byp4ss}"),
    (11, 8311, "Deserialization",     "CVE-2026-68771",  "ComfyUI (pickle)",         "FLAG{comfyui_unauth_p1ckl3_rce}"),
    (12, 8312, "Deserialization",     "CVE-2026-70554",  "MaxSite CMS (PHP)",        "FLAG{maxsite_php_0bject_1nj3ct10n}"),
    (13, 8313, "AI config RCE",       "CVE-2026-84202",  "ModelScope (YAML)",        "FLAG{modelscope_yaml_l0ader_rce}"),
    (14, 8314, "AI agent abuse",      "CVE-2026-102697", "Ollama",                   "FLAG{ollama_pr3f1x_appr0val_byp4ss}"),
    (15, 8315, "Non-HTTP auth",       "CVE-2026-75854",  "ArcadeDB (RESP/TCP)",      "FLAG{arcadedb_resp_m1ss1ng_auth}"),
]
FLAGS = {c[5]: c[0] for c in CH}
app = Flask(__name__)

PAGE = """<!doctype html><meta charset=utf-8><title>The Backlog</title>
<style>
 body{{font:15px -apple-system,Segoe UI,Arial;max-width:900px;margin:36px auto;padding:0 18px;color:#16202a}}
 h1{{margin:0;color:#b02a37}} .sub{{color:#7a8798;margin:4px 0 20px}}
 table{{border-collapse:collapse;width:100%}} td,th{{border-bottom:1px solid #e6eaf0;padding:8px 10px;text-align:left;font-size:14px}}
 th{{color:#5a6472;font-weight:600}} .cat{{font-weight:600}} code{{background:#eef2f8;padding:1px 5px;border-radius:4px}}
 a{{color:#2f6df6;text-decoration:none}} input{{padding:8px;width:340px}} button{{padding:8px 14px;background:#b02a37;color:#fff;border:0;border-radius:6px}}
 #msg{{margin-left:10px;font-weight:600}}
</style>
<h1>\U0001f41e The Backlog</h1>
<p class="sub">15 unpatched H2-2026 CVEs. One per row. Solve in any order; submit <code>FLAG{{...}}</code> below.</p>
<form onsubmit="sub(event)"><input id=f placeholder="FLAG{{...}}" autocomplete=off>
<button>Submit</button><span id=msg></span></form>
<p></p>
<table><tr><th>#</th><th>Category</th><th>CVE</th><th>Product</th><th>Target</th></tr>
{rows}
</table>
<script>
async function sub(e){{e.preventDefault();let v=document.getElementById('f').value.trim();
 let r=await fetch('/submit',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{flag:v}})}});
 let j=await r.json();let m=document.getElementById('msg');
 m.textContent=j.correct?('✓ correct — challenge '+j.num):'✗ not a valid flag';
 m.style.color=j.correct?'#1a7f37':'#b02a37';}}
</script>"""

@app.get("/")
def board():
    host = (request.host or "localhost").split(":")[0]
    rows = "\n".join(
        f'<tr><td>{n}</td><td class="cat">{cat}</td><td><code>{cve}</code></td><td>{prod}</td>'
        f'<td><a href="http://{host}:{port}/" target=_blank>:{port}</a></td></tr>'
        for (n, port, cat, cve, prod, _flag) in CH)
    return Response(PAGE.format(rows=rows), mimetype="text/html")

@app.post("/submit")
def submit():
    flag = (request.get_json(silent=True) or {}).get("flag", "").strip()
    num = FLAGS.get(flag)
    return jsonify(correct=num is not None, num=num)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, threaded=True)
