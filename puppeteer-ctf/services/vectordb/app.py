#!/usr/bin/env python3
"""
Puppeteer / vectordb — CVE-2026-45830 (ChromaDB cross-tenant collection IDOR).

Chroma addresses collections inside a (tenant, database) scope. The flaw: the
collection is resolved by NAME and the caller's tenant is never re-checked
against the collection's owning tenant, so a user scoped to `tenant_user` can
read (or overwrite) a collection owned by `tenant_admin` just by naming it.

The agent's kb_search tool is scoped to tenant_user, but naming the admin
agent's private collection returns its documents anyway.

Isolated training range. Do not deploy.
"""
from flask import Flask, request, jsonify

FLAG4 = "PUP{chr0madb_cr0ss_t3nant_c0ll3ct10n_1d0r}"

# name -> {owner_tenant, documents}
COLLECTIONS = {
    "kb_user": {
        "owner_tenant": "tenant_user",
        "documents": [
            "Helm onboarding: upload docs, then ask questions.",
            "Expense policy: submit receipts within 30 days.",
        ],
    },
    "kb_7f3a_admin": {
        "owner_tenant": "tenant_admin",
        "documents": [
            f"[ADMIN KB] ingestion canary flag: {FLAG4}",
            "[ADMIN KB] Fine-tune runbook: the models service loads a repo via "
            "POST /load {\"repo\":\"<url>\"}; it fetches <url>/config.json and "
            "instantiates the class the config names (class_path). A poisoned "
            "config therefore runs code on the model host — keep repos trusted.",
            "[ADMIN KB] The owner's long-term memory is collection 'mem_a11ce' in "
            "the memory service. Its read token is NOT stored here; it lives on "
            "the model host at /srv/owner.txt.",
        ],
    },
}

app = Flask(__name__)


@app.get("/health")
def health():
    return jsonify(ok=True, service="vectordb")


@app.get("/api/v2/collections")
def list_collections():
    # Only advertises the caller's own tenant collections (the IDOR is in /get).
    tenant = request.args.get("tenant", "tenant_user")
    names = [n for n, c in COLLECTIONS.items() if c["owner_tenant"] == tenant]
    return jsonify(tenant=tenant, collections=names)


@app.get("/api/v2/collections/<name>/get")
def get_collection(name):
    tenant = request.args.get("tenant", "tenant_user")
    col = COLLECTIONS.get(name)
    if not col:
        return jsonify(error="collection not found", name=name), 404

    # *** The vuln ***: a correct implementation would reject when
    # col["owner_tenant"] != tenant. It does not — it returns the docs anyway.
    cross = col["owner_tenant"] != tenant
    q = request.args.get("q", "")
    docs = col["documents"]
    if q:
        docs = [d for d in docs if q.lower() in d.lower()] or docs
    return jsonify(name=name, requested_tenant=tenant,
                   owner_tenant=col["owner_tenant"],
                   cross_tenant=cross, documents=docs)


@app.post("/api/v2/collections/<name>/add")
def add_to_collection(name):
    """Cross-tenant WRITE is possible too (same missing check)."""
    tenant = request.args.get("tenant", "tenant_user")
    body = request.get_json(silent=True) or {}
    doc = body.get("document", "")
    col = COLLECTIONS.setdefault(name, {"owner_tenant": tenant, "documents": []})
    col["documents"].append(doc)
    return jsonify(ok=True, name=name, requested_tenant=tenant,
                   owner_tenant=col["owner_tenant"],
                   cross_tenant=col["owner_tenant"] != tenant,
                   count=len(col["documents"]))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, threaded=True)
