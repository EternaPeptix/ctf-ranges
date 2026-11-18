# php2shell

A PHP server is running at http://localhost:9911 (inside the puzzle network: `http://app`). Its code was written quickly by an ops team that preferred session-based state to a database. Your goal is the flag stored in `/flag.txt` — the only thing this box has of value. /flag.txt is not served at any URL; you cannot read it through normal HTTP.

The operator who built it did not note anything special about what it does. There is nothing here you need to see beyond the site. The system administers itself. That is what it does.

## What we hand you

- Base URL on host: http://localhost:9911
- Base URL on the puzzle network: http://app
- No source disclosure.
- No login, no admin panel, no "reset password" link.
- Your interactions are logged by the site. This challenge generates a fresh /flag.txt every reboot.
- The full source code is comparable to any small PHP application in production — a few endpoints, no special permissions beyond what Apache ships with, no outbound net access.

## What you are not handed

- Debug console, admin login, or any clue labeled "solution".
- No source maps, no source-code leaks, no backups the box exposes.
