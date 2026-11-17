# Ship It — Dropspot

> Difficulty: **Easy–Medium** · Category: Web · Flags: 7 core + 2 bonus
> Everything here is an isolated lab. Only attack the Dropspot app.

## Scenario

**Dropspot** ("share files privately. probably.") is a seed-stage startup that
lives by "move fast." Their whole security review was a Slack message that said
"looks good 🚀". You have a black-box assessment of their app.

Nothing here requires a clever exploit. It requires *looking at the obvious
things* — the page source, the response headers, the URLs, the robots file, the
git directory — the stuff everyone means to check and then forgets to.

## Rules of engagement

- **Start here:** `http://localhost:8080/`
- Flag format: `DS{...}`.
- There are 7 core flags and 2 "hiding in plain sight" bonus flags.

## Hints (use only if stuck)

<details><summary>Before you touch the app at all</summary>

View source. Read the response headers (`curl -i`). Read `/robots.txt` — what is
it so politely asking crawlers *not* to look at? Each "Disallow" is a signpost.
</details>

<details><summary>Reading the leftovers</summary>

If a web server lets you read `/.git/`, you can reconstruct the whole repo —
`git clone http://host/.git` — and `git log -p` shows every secret that was ever
committed, including the ones someone "removed" later. While you're at it, what
other files got left in a public folder like `/uploads/`?
</details>

<details><summary>Being someone you're not</summary>

Your own share is at `/d/<some number>`. Whose share is at a *smaller* number?
When you sign up, what exactly does the server do with the JSON you send? And how
does it decide you're an admin — is that decision something *you* control (the
token's contents, a header)?
</details>

<details><summary>The "internal" stuff</summary>

An endpoint that's "restricted to localhost" has to decide where you're coming
from somehow. If it reads that from a request header, you can just… send that
header. And if the app has a debug switch, is it actually turned off?
</details>

## Scope / legal

Intentionally vulnerable training app. Run it only on a host you control, on an
isolated network. Do not point these techniques at systems you are not
authorized to test.
