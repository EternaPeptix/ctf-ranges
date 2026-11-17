#!/usr/bin/env python3
"""
Keyhaven Vault  —  vault.corp.keyhaven.example  (document renderer)

Faithful re-implementation of CVE-2020-14343: PyYAML's `full_load`/FullLoader
(<= 5.3.1) still resolves dangerous Python object tags, so a crafted document
that builds a `type` with `extend` bound to `exec` and supplies `listitems`
executes attacker Python during parsing — an incomplete fix of the earlier
"load is unsafe" issue. The internal config importer feeds untrusted YAML
straight into full_load.

Isolated training range — do not deploy.
"""
import os
import yaml
from flask import Flask, request, Response

app = Flask(__name__)

FLAG6 = "KH{pyyaml_full_l0ad_typ3_ext3nd_3x3c_byp4ss}"

os.makedirs("/opt/vault", exist_ok=True)
with open("/opt/vault/FLAG6.txt", "w") as fh:
    fh.write(
        FLAG6 + "\n"
        "next: signer.corp.keyhaven.example signs release manifests with ECDSA,\n"
        "but its per-signature nonces are biased (derived from a truncated hash,\n"
        "so the top bits are always zero). Collect signatures from POST /sign and\n"
        "recover the private key via the Hidden Number Problem / lattice reduction\n"
        "(CVE-2024-31497). GET /signer/pubkey and /sign to begin.\n")

OUT = "/tmp/yaml_out"


@app.route("/")
def home():
    return Response("Keyhaven Vault · document renderer. POST a YAML manifest to /import.\n",
                    mimetype="text/plain")


@app.route("/import", methods=["POST"])
def do_import():
    body = request.get_data()
    try:
        if os.path.exists(OUT):
            os.remove(OUT)
    except OSError:
        pass
    try:
        obj = yaml.full_load(body)            # CVE-2020-14343 sink
    except Exception as e:                    # noqa: BLE001
        obj = f"parse error: {e}"
    # Surface any output the imported manifest chose to write (RCE result).
    if os.path.exists(OUT):
        try:
            return Response(open(OUT).read(), mimetype="text/plain")
        except OSError:
            pass
    return Response(f"imported manifest: {obj!r}\n", mimetype="text/plain")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
