#!/usr/bin/env python3
"""VitaChain — scoreboard. Lists the 6 widgets and checks submitted flags."""
from flask import Flask, request, jsonify, Response

# (num, port, name, category, based_on, flag)
CH = [
    (1, 8701, "settle",     "Crypto payment",      "CVE-2026-9189 / H1 #682617",   "FLAG{settle_signed_webhook_never_bound_the_amount_4c1a7e}"),
    (2, 8702, "ledger",     "Crypto on-chain",     "H1 #300748 (Coinbase)",        "FLAG{ledger_credited_a_reverted_transaction_b9f330}"),
    (3, 8703, "rebate",     "Business logic / race","H1 #759247 (Reverb)",         "FLAG{rebate_check_then_credit_is_not_atomic_2e7d64}"),
    (4, 8704, "warehouse",  "SSRF / infra",        "H1 #1369312 / #632101",        "FLAG{warehouse_dns_rebind_toctou_imds_7a21e9}"),
    (5, 8705, "passport",   "Auth / crypto",       "H1 #1210502 (JWT confusion)",  "FLAG{passport_rsa_pubkey_from_sigs_then_hs256_d15ea5}"),
    (6, 8706, "storefront", "API / IDOR",          "H1 #2207248 / #2166697",       "FLAG{storefront_opaque_ids_batched_past_the_limit_88c0de}"),
]
FLAGS = {c[5]: c[0] for c in CH}
app = Flask(__name__)

PAGE = """<!doctype html><meta charset=utf-8><title>VitaChain</title>
<style>
 body{{font:15px -apple-system,Segoe UI,Arial;max-width:900px;margin:36px auto;padding:0 18px;color:#07231a;background:#f3fbf6}}
 h1{{margin:0;color:#0f9d58}} .sub{{color:#5d7a6c;margin:4px 0 20px}}
 table{{border-collapse:collapse;width:100%}} td,th{{border-bottom:1px solid #d7ece0;padding:9px 10px;text-align:left;font-size:14px}}
 th{{color:#4a6b5b;font-weight:600}} .name{{font-weight:700;color:#0b7a43}} .cat{{color:#5d7a6c}}
 code{{background:#e4f5ec;padding:1px 5px;border-radius:4px}}
 a{{color:#0f9d58;text-decoration:none}} input{{padding:8px;width:380px}}
 button{{padding:8px 14px;background:#0f9d58;color:#fff;border:0;border-radius:6px}}
 #msg{{margin-left:10px;font-weight:600}}
</style>
<h1>\U0001f9ea VitaChain</h1>
<p class="sub">Premium supplements, on-chain checkout. Six flaws at the web ↔ crypto-payment seam,
each re-implemented from a real disclosed HackerOne report. <b>Extremely hard.</b> Submit <code>FLAG{{...}}</code>.</p>
<form onsubmit="sub(event)"><input id=f placeholder="FLAG{{...}}" autocomplete=off>
<button>Submit</button><span id=msg></span></form>
<p></p>
<table><tr><th>#</th><th>Widget</th><th>Category</th><th>Based on</th><th>Target</th></tr>
{rows}
</table>
<script>
async function sub(e){{e.preventDefault();let v=document.getElementById('f').value.trim();
 let r=await fetch('/submit',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{flag:v}})}});
 let o=await r.json();let m=document.getElementById('msg');
 m.textContent=o.correct?('✓ correct — widget '+o.num):'✗ not a valid flag';
 m.style.color=o.correct?'#0b7a43':'#b02a37';}}
</script>"""


@app.get("/")
def board():
    host = (request.host or "localhost").split(":")[0]
    rows = "\n".join(
        f'<tr><td>{n}</td><td class="name">{name}</td><td class="cat">{cat}</td>'
        f'<td><code>{src}</code></td><td><a href="http://{host}:{port}/" target=_blank>:{port}</a></td></tr>'
        for (n, port, name, cat, src, _flag) in CH)
    return Response(PAGE.format(rows=rows), mimetype="text/html")


@app.post("/submit")
def submit():
    flag = (request.get_json(silent=True) or {}).get("flag", "").strip()
    num = FLAGS.get(flag)
    return jsonify(correct=num is not None, num=num)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, threaded=True)
