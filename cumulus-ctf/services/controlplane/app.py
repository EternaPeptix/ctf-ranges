#!/usr/bin/env python3
"""
Cumulus / controlplane — a mock cloud API (S3 + IAM + STS). Requests are
authenticated by an access-key id (header X-Cloud-Access-Key or ?AccessKeyId=;
SigV4 is omitted for the range). Each key maps to an identity whose policies
decide what it can do.

Stage 2 — S3 misconfig: the web instance role can read the private `cumulus-backups`
bucket, which holds a flag and a devops IAM user's access key.
Stage 3 — IAM privesc: the devops user holds `iam:CreatePolicyVersion` on its OWN
policy, so it can rewrite that policy to Allow *:* and become admin.

Isolated training range. Do not deploy.
"""
import fnmatch
from flask import Flask, request, jsonify

FLAG2 = "CLD{s3_bucket_m1sc0nf1g_r34d_th3_b4ckups}"
FLAG3 = "CLD{1am_cr34t3p0l1cyv3rs10n_pr1v3sc_t0_4dm1n}"
# shared with the kubeapi service (EKS get-token result for a cluster-admin)
EKS_ADMIN_TOKEN = "k8s-aws-v1.eyJjdW11bHVzIjoiYWRtaW4ifQ.master"

# access key -> identity
IDENTITIES = {
    "ASIACUMULUSINSTANCE01": {"arn": "role/cumulus-web-instance", "policies": ["instance-policy"]},
    "AKIADEVOPS0000STAGE2":  {"arn": "user/devops-ci",            "policies": ["devops-policy"]},
}
# policy name -> list of statements {Action, Resource}
POLICIES = {
    "instance-policy": [
        {"Action": "s3:ListBucket", "Resource": "cumulus-backups"},
        {"Action": "s3:GetObject",  "Resource": "cumulus-backups/*"},
    ],
    "devops-policy": [
        # the misconfig: the user may rewrite its own policy
        {"Action": "iam:CreatePolicyVersion", "Resource": "policy/devops-policy"},
        {"Action": "iam:Get*",                "Resource": "*"},
        {"Action": "sts:GetCallerIdentity",   "Resource": "*"},
    ],
}
BUCKETS = {
    "cumulus-backups": {
        "README.txt": "Nightly backups of the cumulus control plane. DO NOT make public.",
        "flag.txt": FLAG2,
        "iam/devops-ci-access-key.json":
            '{"UserName":"devops-ci","AccessKeyId":"AKIADEVOPS0000STAGE2",'
            '"SecretAccessKey":"devopsSecretKeyEXAMPLE","note":"CI deploy user"}',
    },
}
app = Flask(__name__)


def caller():
    key = request.headers.get("X-Cloud-Access-Key") or request.args.get("AccessKeyId")
    return key, IDENTITIES.get(key)


def allowed(ident, action, resource):
    if not ident:
        return False
    for pname in ident["policies"]:
        for stmt in POLICIES.get(pname, []):
            if fnmatch.fnmatch(action, stmt["Action"]) and fnmatch.fnmatch(resource, stmt["Resource"]):
                return True
    return False


def is_admin(ident):
    if not ident:
        return False
    for pname in ident["policies"]:
        for stmt in POLICIES.get(pname, []):
            if stmt.get("Action") == "*" and stmt.get("Resource") == "*":
                return True
    return False


@app.get("/health")
def health():
    return jsonify(ok=True, service="controlplane")


# ------------------------------- S3 ---------------------------------------- #
@app.get("/s3/<bucket>")
def list_bucket(bucket):
    key, ident = caller()
    if not allowed(ident, "s3:ListBucket", bucket):
        return jsonify(error="AccessDenied", action="s3:ListBucket", resource=bucket), 403
    b = BUCKETS.get(bucket) or {}
    return jsonify(Bucket=bucket, Keys=sorted(b.keys()))


@app.get("/s3/<bucket>/<path:key>")
def get_object(bucket, key):
    _, ident = caller()
    if not allowed(ident, "s3:GetObject", f"{bucket}/{key}"):
        return jsonify(error="AccessDenied", action="s3:GetObject", resource=f"{bucket}/{key}"), 403
    b = BUCKETS.get(bucket) or {}
    if key not in b:
        return jsonify(error="NoSuchKey"), 404
    return jsonify(Bucket=bucket, Key=key, Body=b[key])


# ------------------------------- IAM --------------------------------------- #
@app.get("/iam/whoami")
def whoami():
    key, ident = caller()
    if not ident:
        return jsonify(error="InvalidClientTokenId"), 403
    admin = is_admin(ident)
    resp = {"AccessKeyId": key, "Arn": ident["arn"], "Policies": ident["policies"],
            "Admin": admin}
    if admin:
        resp["flag"] = FLAG3        # you escalated to effectively *:*
    return jsonify(resp)


@app.post("/iam/CreatePolicyVersion")
def create_policy_version():
    _, ident = caller()
    body = request.get_json(silent=True) or {}
    pname = body.get("PolicyName", "")
    doc = body.get("PolicyDocument", {})
    if not allowed(ident, "iam:CreatePolicyVersion", f"policy/{pname}"):
        return jsonify(error="AccessDenied", action="iam:CreatePolicyVersion",
                       resource=f"policy/{pname}"), 403
    stmts = doc.get("Statement", [])
    if isinstance(stmts, dict):
        stmts = [stmts]
    POLICIES[pname] = stmts          # *** rewrite the policy — now attacker-chosen ***
    return jsonify(PolicyName=pname, SetAsDefault=True, Statements=stmts)


# ------------------------------- STS --------------------------------------- #
@app.get("/sts/eks-get-token")
def eks_get_token():
    _, ident = caller()
    if not is_admin(ident):
        return jsonify(error="AccessDenied", note="only a cluster-admin principal may mint an EKS token"), 403
    return jsonify(status={"token": EKS_ADMIN_TOKEN})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, threaded=True)
