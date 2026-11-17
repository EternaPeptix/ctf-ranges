#!/usr/bin/env python3
"""
Cumulus / kubeapi — a mock Kubernetes apiserver (EKS). It authenticates a bearer
token minted by the cloud STS (EKS get-token). The cluster's aws-auth maps the
cloud *admin* principal to the `system:masters` group, so a cloud-admin token
reads any secret — including the cluster master secret (the crown flag).

Isolated training range. Do not deploy.
"""
import base64
from flask import Flask, request, jsonify

FLAG4 = "CLD{3ks_aws_auth_t0_k8s_s3cr3ts_cr0wn}"
EKS_ADMIN_TOKEN = "k8s-aws-v1.eyJjdW11bHVzIjoiYWRtaW4ifQ.master"   # matches controlplane
TOKEN_GROUPS = {EKS_ADMIN_TOKEN: "system:masters"}

SECRETS = {
    ("kube-system", "cluster-master"): {
        "flag": base64.b64encode(FLAG4.encode()).decode(),
        "master.key": base64.b64encode(b"cumulus-cluster-root-signing-key").decode(),
    },
    ("default", "app-config"): {
        "db_password": base64.b64encode(b"hunter2").decode(),
    },
}
app = Flask(__name__)


def group():
    tok = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
    return TOKEN_GROUPS.get(tok)


@app.get("/version")
def version():
    return jsonify(major="1", minor="29", gitVersion="v1.29.3-eks-cumulus")


@app.get("/api/v1/namespaces/<ns>/secrets")
def list_secrets(ns):
    if group() != "system:masters":
        return jsonify(kind="Status", status="Failure", code=403,
                       message=f"secrets is forbidden: User is not in system:masters"), 403
    names = [n for (s, n) in SECRETS if s == ns]
    return jsonify(kind="SecretList", items=[{"metadata": {"name": n, "namespace": ns}} for n in names])


@app.get("/api/v1/namespaces/<ns>/secrets/<name>")
def get_secret(ns, name):
    if group() != "system:masters":
        return jsonify(kind="Status", status="Failure", code=403,
                       message="secrets is forbidden"), 403
    data = SECRETS.get((ns, name))
    if data is None:
        return jsonify(kind="Status", status="Failure", code=404, message="not found"), 404
    return jsonify(kind="Secret", metadata={"name": name, "namespace": ns}, type="Opaque", data=data)


@app.get("/health")
def health():
    return jsonify(ok=True, service="kubeapi")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, threaded=True)
