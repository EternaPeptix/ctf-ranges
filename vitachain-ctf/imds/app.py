#!/usr/bin/env python3
"""Mock cloud instance-metadata service (IMDS) for the warehouse (c4) challenge.
Only reachable inside vitachain_net at hostname `imds` (169.254.169.254 analogue).
Link-local IMDS has no auth — reaching it at all is the whole game."""
from flask import Flask, jsonify, Response

# The "stolen credential" IS the flag — exfiltrated only via the SSRF rebind.
FLAG = "FLAG{warehouse_dns_rebind_toctou_imds_7a21e9}"
ROLE = "vitachain-warehouse-fetcher"

app = Flask(__name__)


@app.get("/latest/meta-data/iam/security-credentials/")
def roles():
    return Response(ROLE + "\n", mimetype="text/plain")


@app.get("/latest/meta-data/iam/security-credentials/<role>")
def creds(role):
    return jsonify({
        "Code": "Success",
        "Type": "AWS-HMAC",
        "AccessKeyId": "ASIAVITACHAINWAREHOUSE",
        "SecretAccessKey": FLAG,                 # <-- the flag is the secret
        "Token": "FwoGZXIvYXdzE…mock…",
        "Expiration": "2030-01-01T00:00:00Z",
    })


@app.get("/")
def root():
    return jsonify(service="imds", hint="/latest/meta-data/iam/security-credentials/")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, threaded=True)
