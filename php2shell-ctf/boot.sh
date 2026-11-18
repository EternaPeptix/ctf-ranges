#!/bin/bash
set -e
php -r '$f = "FLAG{" . bin2hex(random_bytes(16)) . "}"; file_put_contents("/flag.txt", $f); chmod("/flag.txt", 0444);'
exec apache2-foreground