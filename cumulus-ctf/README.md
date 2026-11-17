# Cumulus

> One cloud breach, start to finish — the modern-infra attack path the series
> barely touched.

**Cumulus** is a single chained kill-chain against a fictional cloud provider.
You start at a public web app's SSRF and walk inward through the exact steps of a
real cloud compromise: metadata theft, a bucket misconfig, an IAM privilege
escalation, and finally the Kubernetes cluster. Flags `CLD{...}`.

```
web (SSRF) → imds → controlplane (S3 / IAM / STS) → kubeapi (EKS)
```

| # | Stage | Technique |
|---|-------|-----------|
| 1 | **Metadata theft** | **SSRF → IMDS** — the public app fetches any URL, so you reach the instance metadata service and steal the instance role's credentials |
| 2 | **Bucket loot** | **S3 misconfig** — the instance role can read the private `cumulus-backups` bucket, which holds a flag and a devops IAM user's access key |
| 3 | **Privilege escalation** | **IAM `CreatePolicyVersion`** — the devops user may rewrite its *own* policy; set it to `Allow *:*` and become admin |
| 4 | **Cluster takeover** | **EKS `aws-auth` → Kubernetes** — the admin principal mints an EKS token that maps to `system:masters`; read the cluster-master secret |

Everything is a **self-contained mock of the cloud services** (no real cloud
account, no Docker socket), so the range is safe to run anywhere. The flaws are
the real ones, though: unfiltered SSRF reaching IMDSv1, a bucket policy that
trusts the wrong principal, a self-service IAM policy edit, and an over-broad
`aws-auth` mapping.

## Run it

```bash
make up        # build + start the platform + scoreboard
make check     # run the full kill-chain solver (proves all 4 flags), exit 0
make down      # stop + remove everything
```

- **Public app (CloudSnap):** http://localhost:8097 — the SSRF entry point
- **Scoreboard:** http://localhost:8507
- **Cloud APIs** (reached with stolen creds): control plane `:8098`, kube api `:8099`

## How you play

From the outside you can only reach the web app. Use its `/fetch?url=` SSRF to
hit the internal metadata service, steal the instance credentials, then use those
credentials directly against the public cloud APIs for the rest of the chain —
exactly as an attacker would pivot from a compromised instance. See
[challenge/BRIEF.md](challenge/BRIEF.md).

## Organizer

- [organizer/FLAGS.md](organizer/FLAGS.md) — flag sheet + the loot chain
- [organizer/SOLUTION.md](organizer/SOLUTION.md) — the full walkthrough
- [organizer/DESIGN-NOTES.md](organizer/DESIGN-NOTES.md) — why it's built this way

> ⚠️ Deliberately misconfigured training services. Do not deploy them anywhere
> reachable.
