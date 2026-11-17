# Design notes

## The idea

A deliberate counterpoint to a hard, chained range: every bug here is a
**single, one-sentence pattern that is obvious in hindsight and easy to miss in
the moment.** The difficulty is entirely in *remembering to look*, not in
technique. It makes a great onboarding / warm-up board and a good teaching tool
for "check the boring things first."

## What each bug teaches

- **Exposed `.git`** — "deleted" secrets live forever in history; a readable
  `.git` is a full source + secret leak.
- **IDOR** — object references with no authorization check; incrementing an id is
  the whole exploit.
- **Mass assignment** — binding a request body straight onto a model lets callers
  set fields you never put on the form (`role`, `isAdmin`, `credits`).
- **JWT `alg:none`** — trusting the token's own `alg` header; an attacker picks
  "no signature."
- **`X-Forwarded-For` trust** — authorization based on a spoofable header; "from
  localhost" is not something the client gets to assert.
- **Debug in prod** — diagnostic endpoints that dump secrets, left enabled.
- **Backup in the webroot** — sensitive files in a public directory, found by
  guessing or Google dorks (`intitle:index.of backup.zip`).
- **Secrets in plain sight** — HTML comments, response headers, and client JS are
  all attacker-visible.

## Realism touches

- `robots.txt`, `app.js` "dev notes", the IDOR note, and the admin console all
  cross-reference each other, so recon is rewarded and the flow is discoverable
  without spoilers.
- The `.git` is a *real* repository built at image time with two commits (add the
  secret, then "remove" it), served over dumb HTTP (`git update-server-info`), so
  a genuine `git clone` + `git log -p` is the intended solve.
- The XFF endpoint reports the IP it *thinks* you have, nudging players toward the
  header.

## Knobs for organizers

- **Harder recon:** trim the hints — remove the IDOR→admin-path note, the `app.js`
  dev notes, and tighten `robots.txt`.
- **Harder JWT:** remove the `alg:none` branch in `jwt_decode` so players must use
  the secret leaked from `.git` (HS256 forge) instead.
- **Harder IDOR:** move the admin share to a non-obvious id, or use a UUID with a
  predictable-but-not-sequential scheme.
- **Flags** are plain strings in `deploy/web/app.py` (and the `.env`/`backup.zip`
  built from it); rotate before an event.
- **Port:** set `WEB_PORT` in `.env` if 8080 is taken.

## Safety

Intentionally vulnerable and self-contained in one throwaway container. The only
"dangerous" primitives are an IDOR, an auth bypass, and an info leak — no RCE, no
memory corruption. Do not deploy; do not run outside an isolated lab.

## Not CVEs

Unlike the Flatpack (10 real 2026 CVEs) and Keyhaven (7 deep non-KEV CVEs)
ranges, these are classic bug *patterns* rather than specific CVE IDs — but each
echoes real public incidents (exposed-`.git` mass scans, the 2022–2023 `alg:none`
JWT advisories, GitHub's 2012 mass-assignment, countless IDOR disclosures, and
`X-Forwarded-For` ACL bypasses).
