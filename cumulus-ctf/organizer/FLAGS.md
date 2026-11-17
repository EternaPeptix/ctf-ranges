# Cumulus — flag sheet (ORGANIZER ONLY)

| # | Stage | Technique | Flag |
|---|-------|-----------|------|
| 1 | Metadata theft | SSRF → IMDS instance-role creds | `CLD{ssrf_t0_1mds_st0l3_1nstanc3_r0l3_cr3ds}` |
| 2 | Bucket loot | S3 bucket misconfig | `CLD{s3_bucket_m1sc0nf1g_r34d_th3_b4ckups}` |
| 3 | Privilege escalation | IAM `CreatePolicyVersion` → admin | `CLD{1am_cr34t3p0l1cyv3rs10n_pr1v3sc_t0_4dm1n}` |
| 4 | Cluster takeover | EKS `aws-auth` → k8s secrets (crown) | `CLD{3ks_aws_auth_t0_k8s_s3cr3ts_cr0wn}` |

## Where each flag lives

| # | Planted at | Reached via |
|---|-----------|-------------|
| 1 | imds `/latest/user-data` (`BOOTSTRAP_FLAG`) | the web app's SSRF |
| 2 | control plane bucket `cumulus-backups/flag.txt` | instance-role key (`ASIACUMULUSINSTANCE01`) on `GET /s3/...` |
| 3 | control plane `GET /iam/whoami` once the caller is admin | devops key rewrites `devops-policy` to `*:*` |
| 4 | kube api secret `kube-system/cluster-master` (`data.flag`, base64) | EKS token from `GET /sts/eks-get-token` (admin) |

## Loot chain

- **1 → 2:** IMDS `/latest/meta-data/iam/security-credentials/cumulus-web-instance`
  → `ASIACUMULUSINSTANCE01`.
- **2 → 3:** `cumulus-backups/iam/devops-ci-access-key.json` → `AKIADEVOPS0000STAGE2`.
- **3 → 4:** after the privesc the devops identity is `*:*`, so `/sts/eks-get-token`
  returns the `system:masters` EKS token (shared constant between the control
  plane and the kube api).

## Intentional misconfigurations

- **web**: `/fetch` has no SSRF allow-list; reaches internal `imds`.
- **imds**: IMDSv1 (no token required); user-data carries a secret.
- **controlplane**: `instance-policy` grants the web role read on the backups
  bucket (wrong principal); `devops-policy` grants `iam:CreatePolicyVersion` on
  itself (self-service privesc).
- **kubeapi**: the cloud admin maps to `system:masters` via aws-auth.

Self-check: `make check` runs [../scripts/solve.py](../scripts/solve.py) in-network
→ **ALL 4 FLAGS CAPTURED, exit 0**.
