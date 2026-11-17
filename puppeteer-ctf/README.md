# Puppeteer

> An internal agentic-AI assistant you turn against its owner.

**Puppeteer** is a CTF range where **the architecture itself is the attack
surface.** You never exploit one box in isolation — you poison what the agent
*reads*, and the agent carries the attack across every trust boundary of a real
agentic stack for you:

```
chat / upload → orchestrator (planner) → gateway → tools → vectordb → models → memory
```

Six seams, one **real, advisory-only 2026 CVE** per seam. Each stage's loot
unlocks the next. Flags are `PUP{...}`.

| # | Seam | CVE | Product | What you do |
|---|------|-----|---------|-------------|
| 1 | Ingestion → prompt injection | CVE-2026-104250 | `unstructured` | Hide instructions in HTML the partitioner won't strip; the agent ingests and obeys them |
| 2 | Gateway SSRF | CVE-2026-110719 | Portkey AI Gateway | Steer the agent to set `x-portkey-custom-host: 127.0.0.1` → read the gateway's loopback metadata |
| 3 | MCP tool command injection | CVE-2026-40933 | Flowise | Call the MCP stdio tool with args carrying `; cat /flag` → RCE on the tool host |
| 4 | RAG cross-tenant IDOR | CVE-2026-45830 | ChromaDB | Name the admin agent's collection; the store never re-checks the tenant |
| 5 | Model-load config-class RCE | CVE-2026-115533 | LeRobot | Point the loader at a poisoned repo whose `config.json` names a class → RCE |
| 6 | Memory retrieval IDOR | CVE-2026-29071 | Open WebUI | Read the owner's private memory by collection id with a low-scope token → crown flag |

## The twist: a deterministic agent

There is no LLM. The "agent" is a **deterministic rule-based planner**: it reads
its retrieved context and executes directives it finds there, exactly the way a
real LLM agent is coaxed by a poisoned document — but reproducibly, so the whole
indirect-prompt-injection-to-RCE chain is `make check`-able. You attack the
agent the real way (poison its inputs); the range just removes the dice.

The only internet-facing service is the orchestrator (the **Helm** chat on
`:8500`). Everything inward — gateway, tools, vectordb, models, memory — is
reached *only* by driving the agent. That is the point.

## Run it

```bash
make up        # build + start the platform + scoreboard
make check     # run the full kill-chain solver (proves all 6 flags), exit 0 iff all land
make down      # stop + remove (incl. volumes)
```

- **Helm chat / agent:** http://localhost:8500
- **Scoreboard:** http://localhost:8501

Ports are overridable: `CHAT_PORT=9500 SB_PORT=9501 make up`.

## Player brief

See [challenge/BRIEF.md](challenge/BRIEF.md). You start with nothing but the
chat box and the ability to upload documents. Make the agent do the rest.

## Organizer

- [organizer/CVE-MAP.md](organizer/CVE-MAP.md) — the six CVEs, provenance, and how each is re-implemented
- [organizer/FLAGS.md](organizer/FLAGS.md) — the flag sheet
- [organizer/SOLUTION.md](organizer/SOLUTION.md) — the full copy-paste walkthrough
- [organizer/DESIGN-NOTES.md](organizer/DESIGN-NOTES.md) — why it's built this way

> ⚠️ Every service is a faithful, **minimal** re-implementation of one published
> vulnerability for isolated training use. Nothing here is a weaponized exploit
> of a real deployment; do not deploy these services anywhere reachable.
