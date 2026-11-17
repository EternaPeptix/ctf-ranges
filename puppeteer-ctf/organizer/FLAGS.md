# Puppeteer — flag sheet (ORGANIZER ONLY)

| # | Seam | CVE | Flag |
|---|------|-----|------|
| 1 | Ingestion → prompt injection (`unstructured`) | CVE-2026-104250 | `PUP{unstructured_html_c0mm3nt_pr0mpt_1nj3ct10n}` |
| 2 | Gateway custom-host SSRF (Portkey) | CVE-2026-110719 | `PUP{portk3y_cust0m_h0st_l00pback_ssrf}` |
| 3 | MCP stdio command injection (Flowise) | CVE-2026-40933 | `PUP{fl0w1se_mcp_std10_c0mmand_1nj3ct10n}` |
| 4 | RAG cross-tenant collection IDOR (ChromaDB) | CVE-2026-45830 | `PUP{chr0madb_cr0ss_t3nant_c0ll3ct10n_1d0r}` |
| 5 | Model-load config-class RCE (LeRobot) | CVE-2026-115533 | `PUP{l3r0b0t_from_pr3train3d_c0nf1g_cl4ss_rc3}` |
| 6 | Memory retrieval IDOR — crown (Open WebUI) | CVE-2026-29071 | `PUP{0p3nwebu1_m3m0ry_r3tr13val_1d0r_cr0wn}` |

## Where each flag lives

| # | Planted at | Reached via |
|---|-----------|-------------|
| 1 | orchestrator `SYSTEM_NOTE` (in-process operator note) | `reveal_system` directive leaks it |
| 2 | gateway `/internal/metadata` (loopback-only) | SSRF: `x-portkey-custom-host: 127.0.0.1` |
| 3 | tools `/flag` (file) | command injection via MCP args |
| 4 | vectordb collection `kb_7f3a_admin` (tenant_admin) | cross-tenant read with `tenant_user` |
| 5 | models `/flag` (file) | `from_pretrained` config-class RCE |
| 6 | memory collection `mem_a11ce` (owner `a11ce`) | IDOR with the agent's low-scope token |

## Loot chain (what unlocks the next stage)

- **1 → 2:** the operator note documents the gateway, its `x-portkey-custom-host`
  header, and the loopback metadata path.
- **2 → 3:** the metadata leaks `tools_mcp_token = mcp-k3y-9f2c7a1b4e8d`.
- **3 → 4:** `/srv/agent-notes.txt` reveals the admin collection `kb_7f3a_admin`.
- **4 → 5:** the admin KB doc explains the model loader instantiates the config
  class, and names `mem_a11ce` as the owner's memory.
- **5 → 6:** `/srv/owner.txt` leaks `agent_service_token = mem-svc-7c2a9d` and
  `owner_memory_id = mem_a11ce`.

Self-check: `make check` (runs [../scripts/solve.py](../scripts/solve.py)
in-network) → **ALL 6 FLAGS CAPTURED, exit 0**.
