# The Backlog

> Difficulty: **Mixed (Easy–Hard)** · Category: Jeopardy / multi-class · Flags: 15
> Everything here is an isolated lab. Only attack the Backlog hosts.

## Scenario

It's the end of H2 2026 and the security team's patch backlog has 15 CVEs on it —
each one a different product, a different bug class, a different box. Nobody has
gotten to them. Your job: prove each is exploitable by pulling its flag.

There is **no chain and no pivot** here — the 15 challenges are independent. Pick
whatever category you like and go.

## Rules of engagement

- **Scoreboard:** `http://localhost:8300/` — the board + where you submit flags.
- **Challenges:** `http://localhost:8301` … `8315`. #15 is a **raw TCP** service,
  not HTTP.
- Flag format: `FLAG{...}`.

## The board

| Port | Category | Product |
|------|----------|---------|
| 8301 | SQL injection | Metacat |
| 8302 | SSTI | Drupal Webform |
| 8303 | SSRF | TikTok Download API |
| 8304 | Local file read | Dompdf |
| 8305 | Upload → RCE | Cockpit CMS |
| 8306 | Argument injection | mcp-server-kubernetes |
| 8307 | XXE | OpenRemote |
| 8308 | IDOR | Termix |
| 8309 | JWT | Moodle o365 |
| 8310 | Authz bypass | Kong Gateway |
| 8311 | Deserialization | ComfyUI |
| 8312 | Deserialization | MaxSite CMS |
| 8313 | AI config RCE | ModelScope |
| 8314 | AI agent abuse | Ollama |
| 8315 | Non-HTTP auth | ArcadeDB (TCP) |

## General hints

Each box tells you a little about itself at `/`. Think about: what the parameter
is concatenated into; whether a "signature" is actually checked; whether an
allowlist is anchored; where an uploaded or deserialized thing ends up; and, for
the AI/cloud boxes, how a tool decides a request is "safe." For #15, speak the
protocol the port expects — and notice it never asks you to log in.

## Scope / legal

Intentionally vulnerable re-implementations of real, disclosed H2-2026 CVEs. Run
only on a host you control, on an isolated network. Do not point these techniques
at systems you are not authorized to test.
