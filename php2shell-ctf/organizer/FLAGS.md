# Flags (organizer)

One flag, **earned** (not hardcoded): a fresh `FLAG{...}` is written to `/flag.txt` at container start by `boot.sh` from `bin2hex(random_bytes(16))`. It is never served as a response; it is only recoverable via PHP code execution on the host.

| Widget | Port | Technique required | Flag |
|--------|------|--------------------|------|
| php2shell | 9911 | PHP session `upload_progress` filename injection → session file inclusion | `FLAG{<32 lowercase hex>}` per boot |

## The technique (why it's the whole point)

PHP's upload progress handler writes the raw filename of any multipart upload to the session file. The session file is a plain text file containing serialized PHP session state, but any bytes that appear in the file are passed to `include` verbatim except the PHP parser, which treats `<?php ... ?>` tags as executable code.

The challenge's `/raw.php` endpoint is unprotected against directory traversal. An attacker can include any path under the filesystem.

    upload progress handler writes raw filename
    → session file at /tmp/sess_<SID>
    → included via /raw.php?page=...&page=../../tmp/sess_SID
    → /flag.txt inlined into the response
