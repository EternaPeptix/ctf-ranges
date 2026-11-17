# Design notes

## The brief: "very distinct from the other CTFs thus far"

The four earlier ranges were all single-theme web services — two chained pivots
(Flatpack, Keyhaven) and two single-app flag collections (Dropspot, Bastion). The
Backlog departs on **structure and breadth**:

- **Jeopardy, not chained.** 15 *independent* challenges, each its own container,
  solvable in any order, tied together by a scoreboard. No pivot, no shared
  narrative.
- **Maximum class spread.** 15 CVEs → ~14 distinct CWE classes: SQLi, SSTI, SSRF,
  LFI, upload-RCE, argument injection, XXE, IDOR, JWT, authz-normalization, pickle
  deser, PHP object injection, AI-YAML-RCE, AI-agent abuse, non-HTTP missing-auth.
- **Modern surface.** Deliberately heavy on the classes none of the prior ranges
  touched — a poisoned model config (ModelScope), an MCP-Kubernetes agent tool
  (mcp-server-kubernetes), an LLM agent runner (Ollama), an API gateway (Kong),
  and a raw Redis-wire service (ArcadeDB).
- **Freshness constraint.** Every CVE was published in **H2 2026** and verified
  against NVD + MITRE; a dozen H1-2026 impostors were caught and dropped.

## Architecture (how 15 challenges stay small)

- **One Python image** (`app/`) serves any Python challenge selected by the
  `$CHALLENGE` env var (`serve.py` imports `challenges/cNN.py` and runs its Flask
  `app`, or its `run()` for the raw-TCP one). 12 containers, one image, one build.
- **Three PHP images** for the genuinely-PHP bugs (Dompdf chroot `strpos`, Cockpit
  `.php` upload, MaxSite `unserialize`).
- **Scoreboard** is a tiny Flask app that lists the board and checks submitted
  flags.
- `scripts/solve.py` runs every exploit **in-network** (by service name) so
  `make check` needs no host ports and no pip.

## Fidelity vs. safety

Each challenge reproduces the real CVE's mechanism (same sink / missing check),
re-implemented minimally — see `CVE-MAP.md` for the per-challenge simplifications
(e.g. c01 is UNION-based rather than error-based; c06 stubs kubectl to make the
token-exfil deterministic). Deliberately unsafe sinks (`pickle.load`,
`yaml.Loader`, `shell=True`, external XML entities, a PHP webshell) are contained
to throwaway containers on one bridge network. **Do not deploy.**

## Knobs for organizers

- **Rotate flags:** they're plain strings in `app/challenges/cNN.py` and the PHP
  `index.php`/Dockerfiles.
- **Swap a category:** `CVE-MAP.md` lists a verified H2-2026 bench (Semaphore,
  Renovate, BusyBox zip-symlink, SAP OAuth-SSRF, OpenAM SAML, Eclipse Milo
  Bleichenbacher, Bifrost spawn-RCE, prototype pollution) to drop in.
- **Ports:** challenges are 8301–8315, scoreboard 8300; edit `docker-compose.yml`
  if any are taken.
- **Add a hard-crypto category:** wire in Eclipse Milo (CVE-2026-60007) from the
  bench for a Bleichenbacher padding-oracle challenge.

## The series so far
- **Flatpack** — 10 real 2026 CVEs, chained, hard to exploit.
- **Keyhaven** — 7 deep non-KEV CVEs, chained, hard to execute.
- **Dropspot** — obvious-once-you-look bugs, easy to find.
- **Bastion** — hard-to-find / trivial-to-exploit needles.
- **The Backlog** — 15 H2-2026 CVEs, jeopardy breadth, AI/cloud/parser/non-HTTP (this one).
