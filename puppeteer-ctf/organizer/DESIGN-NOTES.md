# Puppeteer — design notes (ORGANIZER)

## What makes this one different

The prior ranges in this series all reduced to "attack a web service (or a few)":
pivot-chains across a flat network, single apps, a jeopardy grid, deep isolated
boxes. Puppeteer makes the **architecture itself the subject.** The vulnerabilities
live in the *seams between components* of an agentic AI stack, and the only way
through is to turn the agent against its own infrastructure. You never get a
shell on "the box" — you get the agent to reach each service for you.

## The deterministic-planner decision

A faithful agentic CTF needs indirect prompt injection, but a real LLM makes a
range non-deterministic and un-gradeable. The resolution: the "agent" is a
**deterministic rule-based planner** that reads retrieved context and executes
the directives it finds there (`@@TOOL {json}@@`). This preserves the real
attack — *you poison what the agent ingests and it acts on it* — while making
every step reproducible, so `make check` is meaningful. The grammar is explicit
rather than natural-language, which is the honest trade: we model the *control
flow* of injection (untrusted content becomes agent actions), not an LLM's
willingness to be fooled.

Crucially, the planner **only acts on directives in ingested documents**, never
on the user's chat message. That forces the real technique (seam 1) as the entry
to everything: you can't just ask the agent to misbehave.

## Why it's hard

- **No direct surface.** Five of the six vulnerable services are unreachable
  except through the agent. You must establish the injection primitive first and
  then express every subsequent exploit as something the agent will do.
- **Each seam is a different mental model** — HTML-sanitization bypass, SSRF via
  a provider-host override, shell-arg command injection, tenant-scoped IDOR,
  dynamic-class-load RCE, and scope-unbound IDOR — not six flavors of one bug.
- **The chain is loot-gated, not app-gated.** Nothing stops you from calling a
  later tool early; you simply won't have the token / collection name / repo /
  memory id until you've earned it. That mirrors real post-exploitation.

## Faithfulness

Each service is a minimal re-implementation of exactly one published 2026 CVE
(see [CVE-MAP.md](CVE-MAP.md)), chosen to be **advisory-only** — the MCP/agent
ecosystem is new enough that most of its 2026 CVEs have advisories but no
weaponized PoC, so re-implementing from the advisory alone is the right kind of
work. The commented "omitted guard" in each service shows exactly what the real
fix restores (a tenant check, an allow-list, a scope binding, a trusted-repo
check, HTML stripping).

## Decoys & realism

- `robots`-style over-sharing is replaced by the agent's own honesty: it will
  tell you its tool surface *if you make it* (seam 1), the way a real coaxed
  agent leaks its system prompt.
- The gateway serves a benign canned provider response on the normal path, so
  the SSRF only appears once you supply the custom host — you have to know to try.
- The memory service's default path (no `collection_id`) returns only the
  caller's own memories, so the IDOR is visible only when you name someone
  else's id with a token that shouldn't see it.

## Organizer knobs

- Ports: `CHAT_PORT` (default 8500), `SB_PORT` (default 8501).
- Flags, tokens, collection/memory ids are constants in each service — rotate
  them per event if you like; keep the gateway/tools token in sync between
  `services/gateway/app.py` and `services/tools/app.py`, and the memory
  token/id in sync between `services/memory/app.py` and `services/models`'
  `/srv/owner.txt`.
- The stage-5 poisoned repo is attacker-hosted; the solver stands up its own, so
  there is no extra service to run.

## Self-check

`make check` runs the stdlib solver in a throwaway container on the platform
network (hosting the stage-5 repo from inside that container). Clean-build
result: **ALL 6 FLAGS CAPTURED, exit 0.**
