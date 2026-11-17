<?php
/* c04 — CVE-2026-55554 : Dompdf chroot bypass.
 * validateLocalUri() checks strpos($real, $chroot) === 0, so a sibling path
 * like /var/www/html-secret matches the /var/www/html prefix and is admitted. */

$CHROOT = "/var/www/html";

function validateLocalUri($uri, $chroot) {
    if (strpos($uri, "file://") !== 0) return false;
    $path = substr($uri, 7);
    $real = realpath($path);
    if ($real === false) return false;
    return strpos($real, $chroot) === 0;      // BUG: prefix check, no trailing separator
}

$src = $_GET["src"] ?? "";
if ($src === "") {
    header("Content-Type: text/plain");
    echo "Dompdf renderer. Resolve a local resource, e.g. ?src=file:///var/www/html/logo.txt\n";
    exit;
}
if (validateLocalUri($src, $CHROOT)) {
    header("Content-Type: text/plain");
    echo file_get_contents(substr($src, 7));
} else {
    http_response_code(403);
    echo "refused: uri is not within the document root";
}
