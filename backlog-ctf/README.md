# The Backlog — CTF range

A **jeopardy-style** CTF: a security team's **unpatched backlog** of **15 real
CVEs published in the second half of 2026**, each re-implemented as its own tiny,
independent container. Solve them in any order; a scoreboard ties them together.

This range is deliberately **broad** rather than chained — a deliberate contrast
to the earlier ranges — and loaded with the **modern AI / cloud / parser /
non-HTTP** classes none of them touched (poisoned-model-config RCE, MCP-Kubernetes
argument injection, LLM-agent tool abuse, API-gateway normalization bypass, a
Redis-wire service with no auth).

> ⚠️ Intentionally vulnerable training range. Run only on an isolated host you
> control. Every service contains a deliberately unsafe sink. Do not deploy.

## The board — 15 CVEs, 15 classes

| # | Category | CVE (publ.) | Product | The bug |
|---|----------|-------------|---------|---------|
| 1 | SQL injection | CVE-2026-48528 (08-14) | NCEAS Metacat | unauth SQLi via `nodeId` |
| 2 | SSTI | CVE-2026-96355 (10-22) | Drupal Webform | form field → Twig/Jinja `{{...}}` |
| 3 | SSRF | CVE-2026-85608 (09-04) | TikTok Download API | unauth `url` fetch, no allowlist |
| 4 | LFI / parser | CVE-2026-55554 (07-28) | Dompdf | `strpos` chroot-prefix bug |
| 5 | Upload → RCE | CVE-2026-72557 (08-11) | Cockpit CMS | wildcard upload → `.php` webshell |
| 6 | Argument injection | CVE-2026-61459 (07-10) | mcp-server-kubernetes | `--server` into kubectl → token exfil |
| 7 | XXE | CVE-2026-54640 (10-13) | OpenRemote | ETS XML external entities |
| 8 | IDOR | CVE-2026-53548 (08-19) | Termix | SSH secret by numeric id |
| 9 | JWT auth bypass | CVE-2026-54733 (07-16) | Moodle `local_o365` | `upn` trusted, no signature check |
| 10 | Authz normalization | CVE-2026-105986 (11-10) | Kong Gateway | `%2F`/`%61` evades RBAC, decodes at backend |
| 11 | Deser (pickle) | CVE-2026-68771 (07-31) | ComfyUI | unauth `.pkl` → `pickle.load` |
| 12 | Deser (PHP) | CVE-2026-70554 (08-04) | MaxSite CMS | cookie → `unserialize()` POP chain |
| 13 | AI config RCE | CVE-2026-84202 (10-21) | ModelScope | `configuration.yaml` via `yaml.Loader` |
| 14 | AI agent abuse | CVE-2026-102697 (09-29) | Ollama | prefix-approved command → shell `; cat /flag` |
| 15 | Non-HTTP auth | CVE-2026-75854 (08-18) | ArcadeDB | Redis-wire plugin, no AUTH gate |

All verified **published 2026-07 .. 2026-12** (NVD `totalResults=1` + MITRE
`PUBLISHED`). Flag format: `FLAG{...}`. Full provenance: [`organizer/CVE-MAP.md`](organizer/CVE-MAP.md).

## Quick start

```bash
cp .env.example .env         # optional
make up                      # build + start all 15 + the scoreboard
```

- Scoreboard: `http://localhost:8300/`
- Challenges: `http://localhost:8301` .. `8315` (c15 is a raw-TCP service)

Prove it all solves (organizer self-check — runs all 15 exploits in-network):

```bash
make check                   # exits 0 iff all 15 flags land
```

Tear down:

```bash
make down
```

## Layout

```
backlog-ctf/
├─ docker-compose.yml        # scoreboard + c01..c15
├─ Makefile                  # up / check / down / reset
├─ app/                      # ONE Python image; serves any challenge by $CHALLENGE
│  ├─ serve.py · Dockerfile
│  └─ challenges/c01.py … c15.py   (the 12 Python challenges)
├─ php/                      # the 3 genuinely-PHP bugs (own images)
│  ├─ c04-dompdf · c05-cockpit · c12-maxsite
├─ scoreboard/               # Flask board + flag checker
├─ scripts/solve.py · verify.sh
└─ organizer/                # CVE-MAP · FLAGS · SOLUTION · DESIGN-NOTES
```

Full walkthrough with payloads: **[`organizer/SOLUTION.md`](organizer/SOLUTION.md)**.
