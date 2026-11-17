#!/usr/bin/env python3
"""Cumulus — scoreboard. The four stages of the cloud kill-chain + flag check."""
import os
from flask import Flask, request, jsonify, Response

WEB_PORT = os.environ.get("WEB_PORT", "8097")

# (num, stage, technique, flag)
CH = [
    (1, "Metadata theft", "SSRF → IMDS instance-role credentials",
     "CLD{ssrf_t0_1mds_st0l3_1nstanc3_r0l3_cr3ds}"),
    (2, "Bucket loot", "S3 bucket misconfig → read the private backups",
     "CLD{s3_bucket_m1sc0nf1g_r34d_th3_b4ckups}"),
    (3, "Privilege escalation", "IAM iam:CreatePolicyVersion → admin",
     "CLD{1am_cr34t3p0l1cyv3rs10n_pr1v3sc_t0_4dm1n}"),
    (4, "Cluster takeover", "EKS aws-auth → Kubernetes secrets (crown)",
     "CLD{3ks_aws_auth_t0_k8s_s3cr3ts_cr0wn}"),
]
FLAGS = {c[3]: c[0] for c in CH}
app = Flask(__name__)

PAGE = """<!doctype html><meta charset=utf-8><title>Cumulus</title>
<style>
 body{{font:15px -apple-system,Segoe UI,Arial;max-width:900px;margin:34px auto;padding:0 18px;background:#0b0f16;color:#dce4ee}}
 h1{{margin:0;color:#6cc1ff}} .sub{{color:#8793a3;margin:4px 0 16px}}
 table{{border-collapse:collapse;width:100%}} td,th{{border-bottom:1px solid #1c2430;padding:9px 10px;text-align:left;font-size:14px}}
 th{{color:#8793a3;font-weight:600}} .t{{font-weight:600;color:#eef3fa}} code{{background:#141c27;padding:1px 5px;border-radius:4px;color:#8fd6ff}}
 a{{color:#6cc1ff;text-decoration:none}} input{{padding:8px;width:380px;background:#101722;border:1px solid #233041;color:#dce4ee;border-radius:6px}}
 button{{padding:8px 14px;background:#2563c9;color:#fff;border:0;border-radius:6px;cursor:pointer}} #m{{margin-left:10px;font-weight:600}}
 .arr{{color:#4a5568}}
</style>
<h1>☁ Cumulus</h1>
<p class="sub">One cloud breach, start to finish. Begin at the public app's SSRF
(<a href="http://localhost:{web_port}/" target=_blank>CloudSnap</a>) and walk it inward.
Each stage's loot unlocks the next. Flags <code>CLD{{...}}</code>.</p>
<form onsubmit="s(event)"><input id=f placeholder="CLD{{...}}" autocomplete=off><button>Submit</button><span id=m></span></form><p></p>
<table><tr><th>#</th><th>Stage</th><th>Technique</th></tr>
{rows}
</table>
<p class="sub" style="margin-top:14px">web (SSRF) <span class=arr>&rarr;</span> imds <span class=arr>&rarr;</span>
 controlplane (S3/IAM/STS) <span class=arr>&rarr;</span> kubeapi</p>
<script>
async function s(e){{e.preventDefault();let v=document.getElementById('f').value.trim();
 let r=await fetch('/submit',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{flag:v}})}});
 let j=await r.json();let m=document.getElementById('m');
 m.textContent=j.correct?('✓ stage '+j.num):'✗ nope';m.style.color=j.correct?'#5fd38d':'#ff6b6b';}}
</script>"""


@app.post("/submit")
def submit():
    flag = (request.get_json(silent=True) or {}).get("flag", "").strip()
    return jsonify(correct=flag in FLAGS, num=FLAGS.get(flag))


@app.get("/")
def board():
    rows = "\n".join(
        f'<tr><td>{n}</td><td class="t">{stage}</td><td>{tech}</td></tr>'
        for (n, stage, tech, _f) in CH)
    return Response(PAGE.format(rows=rows, web_port=WEB_PORT), mimetype="text/html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, threaded=True)
