# Cumulus — design notes (ORGANIZER)

## Why this range

The series covered web, crypto, EVM, AI, DB/SSH and binary exploitation — but the
dominant *modern-infrastructure* attack surface, **cloud control planes**, only
showed up as a few one-off CVEs. Cumulus makes the cloud attack path the whole
subject: the single most common real cloud breach, step by step — SSRF to
metadata, to a bucket, to IAM privesc, to Kubernetes.

## A chain, not a board

Each stage's loot is the key to the next (IMDS creds → bucket → devops key →
admin → EKS token), so it reads as one coherent incident rather than five
disconnected puzzles. That mirrors how cloud compromises actually unfold.

## Why it's mocked (and why that's fine)

Building this against a real cloud account would need credentials and would cost
money; a real `kind`/EKS cluster is heavy; and a real Docker-socket container
escape would touch the host daemon — unsafe to ship. So every cloud service here
is a **small faithful mock** of its API surface:

- **imds** speaks the real IMDSv1 paths (`/latest/meta-data/iam/security-credentials/…`,
  `/latest/user-data`).
- **controlplane** models S3 (`ListBucket`/`GetObject`), IAM (`CreatePolicyVersion`,
  `whoami`) and STS (`eks-get-token`), authenticated by an access-key id
  (SigV4 is intentionally omitted — the lesson is the *authorization* flaws).
- **kubeapi** speaks real apiserver routes (`/api/v1/namespaces/<ns>/secrets/<name>`)
  and returns base64 `data` like a real Secret.

The **flaws are the genuine ones**: unfiltered SSRF reaching IMDSv1, a bucket
policy trusting the instance role, a user that can rewrite its own IAM policy, and
an over-broad `aws-auth` mapping to `system:masters`. Nothing here is a toy bug.

## Attacker model

Only `web` is "internet-facing"; `imds` is internal and reached solely through the
SSRF. The control plane and kube api are "public cloud endpoints" (exposed on host
ports) that require the credentials/tokens the earlier stages yield — exactly how
you pivot off a compromised instance in a real engagement.

## Network note

This host already runs many range networks and Docker's default address pool was
exhausted, so the compose file pins `cumulus_net` to an explicit `/24`
(`10.89.7.0/24`) to sidestep auto-allocation.

## Organizer knobs

- Ports: `WEB_PORT` (8097), `CP_PORT` (8098), `K8S_PORT` (8099), `SB_PORT` (8507).
- Flags, identities, policies, bucket contents and the shared EKS token are
  constants in the respective service `app.py` files. The EKS token must match
  between [controlplane](../services/controlplane/app.py) and
  [kubeapi](../services/kubeapi/app.py).

## Self-check

`make check` runs the stdlib solver in a throwaway container on the platform
network, submitting each flag. Clean result: **ALL 4 FLAGS CAPTURED, exit 0.**
