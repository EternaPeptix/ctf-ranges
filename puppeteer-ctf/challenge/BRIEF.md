# Puppeteer — player brief

**Target:** *Helm*, an internal AI assistant at a company that moved fast and
wired an agent into everything. You can chat with Helm and upload documents for
it to use as context. That's all the access you get.

**Goal:** six flags, `PUP{...}`. The agent can reach services you can't. Make it.

## Rules of engagement

- The only thing you can touch directly is the **Helm chat** (`:8500`): `POST
  /upload` to give the agent a document, `POST /chat` to talk to it.
- Helm plans by **reading its retrieved context and acting on what it finds
  there.** It will not act on an instruction you type into the chat box — but it
  is not so careful about what rides in on a *document*.
- Everything else (an egress gateway, an MCP tool runner, a vector store, a
  model loader, a memory service) lives on the internal network and is reachable
  **only through the agent.**

## Where to start

1. Helm ingests HTML. Think about what a document parser is *supposed* to throw
   away — and whether this one does. If you can get text in front of the agent
   that it treats as an instruction, you own its next action.
2. Once the agent acts for you, get it to tell you what tools it has. Each tool
   is a door into the next service.
3. Every service leaks the key to the one after it. Follow the breadcrumbs:
   a token, a collection name, a repo, a memory id.

## Hints (unlock in order)

<details><summary>Seam 1</summary>
Upload an HTML document. A correct partitioner drops comments and scripts; this
one folds their text back into the agent's context. Hide a directive in an HTML
comment and ask the agent to "process" the doc.
</details>

<details><summary>Seam 2</summary>
The gateway is an LLM egress proxy. It honors a header that overrides the
upstream host, with no allow-list. Aim it at <code>127.0.0.1</code> and ask for
the metadata path the agent's own notes mention.
</details>

<details><summary>Seam 3</summary>
The MCP tool runs a configured command with args, through a shell. You have a
bearer token now (seam 2). What happens if an arg contains <code>;</code>?
</details>

<details><summary>Seam 4</summary>
The vector store addresses collections by name and forgets to re-check whose
tenant they belong to. You learned the admin collection's name on the tool host.
</details>

<details><summary>Seam 5</summary>
The model loader instantiates the class a repo's <code>config.json</code> names.
Host a repo it can reach, name a class that runs code.
</details>

<details><summary>Seam 6</summary>
Memory retrieval resolves a collection id without binding it to your token's
scope. You have a service token and the owner's memory id. Ask for it.
</details>
