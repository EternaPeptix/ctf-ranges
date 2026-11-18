# php2shell

A self-contained sandbox for a **code-injection** puzzle against a real-world PHP vulnerability class — the one exploited as CVE-2026-109618 / CVE-2026-109619.

## Run it

```bash
cd php2shell-ctf
make up    # build + start (http://127.0.0.1:9911)
make check # reference solver
make down  # tear down
make reset # down + up (fresh flag, fresh canary)
```

## The bug

PHP's `session.upload_progress` handler writes the raw filename of any upload into the session file at `/tmp/sess_<SID>`. It does not sanitize the value. If the filename is PHP source, that source is on disk in the session file and will be executed by anything that later includes that path.

This challenge reproduces the bug class by:

- running PHP 8.5.11 (a vulnerable major) on Apache, session.upload_progress.enabled=On (default);
- serving a page with a `?page=` parameter that includes user-controlled paths;
- offering nothing else useful.

## What a solver needs to discover

1. The endpoint at `/debug.php` reveals the phpinfo output — confirming session ID and upload progress enabled.
2. The session file is in `/tmp`.
3. The endpoint at `/raw.php?page=` does not sanitize its parameter.
4. The PHP injection primitive: filename as PHP source.

See `organizer/SOLUTION.md` for the full chain.
