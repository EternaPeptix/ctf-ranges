# Design notes

## The brief

"Extremely difficult to get the flags but trivial if you know the solution."

So the design rule for every challenge was: **the discovery is the whole
difficulty; the exploit is a one-liner.** No brute force, no long fuzzing, no
multi-step exploit dev. You either recognize the tell or you don't — and the app
hands you exactly what the technique needs once you do.

## Why each one fits the brief

| Needle | Why it's hard to *find* | Why it's trivial once *known* |
|--------|-------------------------|-------------------------------|
| zero-width stego | the data is literally invisible; nothing on screen hints at it | one filter + a binary decode |
| NFKC vs `lower()` | you must suspect two different equality checks *and* know a fold | one crafted username |
| ECB cut-and-paste | you must notice ECB from repeated blocks and know Cryptopals 13 | splice two ciphertexts |
| MD5 length extension | you must recognize `md5(secret‖data)` and know the attack exists | a known routine (or hashpump) |
| unanchored regex | you must infer the allowlist is a substring search | append the magic substring |

## What makes it fair (not just obscure)

Each challenge gives the solver the *oracle or sample the technique requires*, in
the open:
- the register endpoint is an **ECB encryption oracle** you fully control;
- `/api/report` literally states the signature scheme and gives a valid pair;
- `/api/preview` documents the internal diagnostics path it proxies;
- the NFKC hint is in the brief ("two notions of equality").

So the difficulty is recognition and technique, not guessing secret paths or
parameters.

## Knobs for organizers

- **Harder C2:** remove the NFKC hint from the BRIEF; require a specific fold.
- **Harder C4:** stop stating the scheme in `/api/report` (make them infer
  `md5(secret‖data)` from the fixed-length hex tag and behavior).
- **Harder C5:** don't print the `/_internal/*` path; make them find it.
- **Easier overall:** add a repeated-block hint to the token, or echo the regex.
- **Flags & secret** live in `deploy/web/app.py`; `ECB_KEY` is random per boot
  (restart to reset), `SIG_KEY` is fixed (its length is the only secret for C4).
- **Port:** set `WEB_PORT` in `.env` if 8080 is taken.

## Safety

One throwaway container. The worst primitives are an ECB forgery, a signature
forgery, and a loopback SSRF to an endpoint that only returns a flag — no RCE, no
data at risk. Do not deploy; isolated lab only.

## The series so far
- **Flatpack** — 10 real 2026 CVEs, chained, hard-to-*exploit*.
- **Keyhaven** — 7 deep non-KEV CVEs, chained, hard-to-*execute* (lattice, etc.).
- **Dropspot** — obvious-once-you-look bugs, easy-to-*find*.
- **Bastion** — hard-to-*find*, trivial-to-exploit needles (this one).
