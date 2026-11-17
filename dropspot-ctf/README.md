# Dropspot CTF — "Ship It"

A **beginner-to-intermediate web CTF** themed around a move-fast startup whose
file-sharing app is riddled with bugs that are **blindingly obvious once you see
them — and incredibly easy to miss in a hurry.** No deep exploitation, no memory
corruption, no crypto: just the facepalms that show up in real assessments all
the time.

> ⚠️ Intentionally vulnerable training app. Run only on an isolated host you
> control. Do not deploy (obviously).

## The bugs (every one a "oh, *of course*")

| # | Bug | The tell |
|---|-----|----------|
| 1 | **Exposed `.git`** | `/.git/` is world-readable → clone it, `git log -p`, the "removed" secret is still in history |
| 2 | **IDOR** | `/d/1007` is your file… so what's at `/d/1`? Just change the number |
| 3 | **Mass assignment** | signup merges your whole JSON — send `"role":"admin"` |
| 4 | **JWT `alg:none`** | the verifier still accepts unsigned tokens; forge an admin one |
| 5 | **`X-Forwarded-For` trust** | the "localhost-only" admin API believes a header you send |
| 6 | **Debug left on** | `/api/config?debug=1` cheerfully dumps the secrets |
| 7 | **Backup in the webroot** | `/uploads/backup.zip` — the nightly DB dump, downloadable |
| B | **Hiding in plain sight** | a flag in an HTML comment, and one in a response header |

Flag format: `DS{...}`.

## Quick start

```bash
cp .env.example .env         # optional; edit WEB_PORT if 8080 is taken
make up                      # build + start
```

- App: `http://localhost:8080/`  — start with `view-source:` and `/robots.txt`.

Prove it all solves (organizer self-check):

```bash
make check                   # runs scripts/verify.sh; exits 0 iff all 7 core flags land
```

Tear down:

```bash
make down
```

## Layout

```
dropspot-ctf/
├─ docker-compose.yml        # one container: the web app
├─ Makefile                  # up / check / down / reset
├─ challenge/BRIEF.md        # hand this to players
├─ deploy/web/
│  ├─ Dockerfile             # builds the app + the exposed .git (secret in history)
│  ├─ app.py                 # the Flask app and all its bugs
│  └─ public/                # index.html (+comment), robots.txt, app.js, uploads/
├─ scripts/verify.sh         # automated solver
└─ organizer/                # FLAGS · SOLUTION · DESIGN-NOTES
```

## Why it's a good teacher

Each bug is a single, recognizable pattern you can describe in one sentence —
and each is something that has shipped to production at real companies more than
once. The lesson isn't "learn a hard technique," it's **"look at the obvious
things first: the source, the headers, the URLs, the robots file, the git dir."**

Full walkthrough: **[`organizer/SOLUTION.md`](organizer/SOLUTION.md)**.
