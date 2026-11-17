#!/usr/bin/env python3
"""
Cumulus / imds — the instance metadata service (an AWS IMDSv1-style analog of
169.254.169.254). It is internal-only, but the web app's SSRF can reach it.
It exposes the instance's IAM role credentials (the stage-2 loot) and leaks the
bootstrap flag in the user-data.

Isolated training range. Do not deploy.
"""
from flask import Flask, jsonify, Response

FLAG1 = "CLD{ssrf_t0_1mds_st0l3_1nstanc3_r0l3_cr3ds}"
ROLE = "cumulus-web-instance"
CREDS = {
    "Code": "Success",
    "Type": "AWS-HMAC",
    "AccessKeyId": "ASIACUMULUSINSTANCE01",
    "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYinstanceKEY",
    "Token": "IQoJb3JpZ2luX2VjEXAMPLEinstanceSessionToken==",
    "Expiration": "2035-01-01T00:00:00Z",
}
app = Flask(__name__)


@app.get("/latest/meta-data/iam/security-credentials/")
def role_list():
    return Response(ROLE, mimetype="text/plain")


@app.get("/latest/meta-data/iam/security-credentials/<role>")
def role_creds(role):
    if role == ROLE:
        return jsonify(CREDS)
    return ("", 404)


@app.get("/latest/meta-data/instance-id")
def instance_id():
    return Response("i-0cumulus0web0node0", mimetype="text/plain")


@app.get("/latest/user-data")
def user_data():
    # user-data often carries bootstrap secrets — a classic SSRF-to-IMDS prize.
    return Response(
        "#!/bin/bash\n"
        "# cumulus web node bootstrap\n"
        f"export BOOTSTRAP_FLAG={FLAG1}\n"
        "echo 'provisioning complete'\n",
        mimetype="text/plain",
    )


@app.get("/")
def root():
    return Response("latest/\n", mimetype="text/plain")


@app.get("/health")
def health():
    return jsonify(ok=True, service="imds")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, threaded=True)
