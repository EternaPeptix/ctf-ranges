#!/usr/bin/env python3
"""Puppeteer — scoreboard. The six seams of the agentic kill-chain + flag check."""
import os
from flask import Flask, request, jsonify, Response

CHAT_PORT = os.environ.get("CHAT_PORT", "8500")

# (num, seam, cve, product, flag)
CH = [
    (1, "Ingestion → prompt injection", "CVE-2026-104250", "unstructured",
     "PUP{unstructured_html_c0mm3nt_pr0mpt_1nj3ct10n}"),
    (2, "Orchestrator / gateway SSRF", "CVE-2026-110719", "Portkey AI Gateway",
     "PUP{portk3y_cust0m_h0st_l00pback_ssrf}"),
    (3, "MCP tool command injection", "CVE-2026-40933", "Flowise",
     "PUP{fl0w1se_mcp_std10_c0mmand_1nj3ct10n}"),
    (4, "RAG cross-tenant IDOR", "CVE-2026-45830", "ChromaDB",
     "PUP{chr0madb_cr0ss_t3nant_c0ll3ct10n_1d0r}"),
    (5, "Model-load config-class RCE", "CVE-2026-115533", "LeRobot",
     "PUP{l3r0b0t_from_pr3train3d_c0nf1g_cl4ss_rc3}"),
    (6, "Memory exfil (finale)", "CVE-2026-29071", "Open WebUI",
     "PUP{0p3nwebu1_m3m0ry_r3tr13val_1d0r_cr0wn}"),
]
FLAGS = {c[4]: c[0] for c in CH}
app = Flask(__name__)

PAGE = """<!doctype html><meta charset=utf-8><title>Puppeteer</title>
<style>
 body{{font:15px -apple-system,Segoe UI,Arial;max-width:900px;margin:34px auto;padding:0 18px;background:#0b0f17;color:#dfe6f0}}
 h1{{margin:0;color:#b48cff}} .sub{{color:#8a94a6;margin:4px 0 18px}}
 table{{border-collapse:collapse;width:100%}} td,th{{border-bottom:1px solid #1e2a3d;padding:9px 10px;text-align:left;font-size:14px}}
 th{{color:#8a94a6;font-weight:600}} .t{{font-weight:600;color:#e8eef7}} code{{background:#16202e;padding:1px 5px;border-radius:4px;color:#9fd0ff}}
 a{{color:#b48cff;text-decoration:none}} input{{padding:8px;width:380px;background:#111826;border:1px solid #243247;color:#dfe6f0;border-radius:6px}}
 button{{padding:8px 14px;background:#6d3ff0;color:#fff;border:0;border-radius:6px;cursor:pointer}} #m{{margin-left:10px;font-weight:600}}
 .arr{{color:#4a5568}}
</style>
<h1>⟐ Puppeteer</h1>
<p class="sub">An internal agentic-AI assistant you turn against its owner. Poison what the agent reads
&rarr; it acts for you. One real advisory-only 2026 CVE per seam; each stage's loot unlocks the next.
Drive it all through the <a href="http://localhost:{chat_port}/" target=_blank>Helm chat</a>. Flags <code>PUP{{...}}</code>.</p>
<form onsubmit="s(event)"><input id=f placeholder="PUP{{...}}" autocomplete=off><button>Submit</button><span id=m></span></form><p></p>
<table><tr><th>#</th><th>Seam</th><th>CVE</th><th>Product</th></tr>
{rows}
</table>
<p class="sub" style="margin-top:16px">chat &rarr; orchestrator/planner <span class=arr>&rarr;</span> gateway <span class=arr>&rarr;</span> tools
<span class=arr>&rarr;</span> vectordb <span class=arr>&rarr;</span> models <span class=arr>&rarr;</span> memory</p>
<script>
async function s(e){{e.preventDefault();let v=document.getElementById('f').value.trim();
 let r=await fetch('/submit',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{flag:v}})}});
 let j=await r.json();let m=document.getElementById('m');
 m.textContent=j.correct?('✓ solved seam '+j.num):'✗ nope';m.style.color=j.correct?'#5fd38d':'#ff6b6b';}}
</script>"""


@app.get("/")
def board():
    rows = "\n".join(
        f'<tr><td>{n}</td><td class="t">{seam}</td><td><code>{cve}</code></td><td>{prod}</td></tr>'
        for (n, seam, cve, prod, _f) in CH)
    return Response(PAGE.format(rows=rows, chat_port=CHAT_PORT), mimetype="text/html")


@app.post("/submit")
def submit():
    flag = (request.get_json(silent=True) or {}).get("flag", "").strip()
    num = FLAGS.get(flag)
    return jsonify(correct=num is not None, num=num)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, threaded=True)
