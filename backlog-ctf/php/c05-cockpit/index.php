<?php
/* c05 — CVE-2026-72557 : Cockpit CMS asset upload with wildcard allowed_uploads.
 * No extension/type check and files land in the web root -> drop a .php webshell. */

$uri = parse_url($_SERVER["REQUEST_URI"], PHP_URL_PATH);

if ($uri === "/api/assets/upload" && $_SERVER["REQUEST_METHOD"] === "POST") {
    $name = $_GET["name"] ?? ($_FILES["file"]["name"] ?? "");
    $data = !empty($_FILES["file"]["tmp_name"])
            ? file_get_contents($_FILES["file"]["tmp_name"])
            : file_get_contents("php://input");
    $name = basename($name);
    if ($name === "") { http_response_code(400); echo "name required"; exit; }
    @mkdir("/var/www/html/uploads", 0777, true);
    file_put_contents("/var/www/html/uploads/" . $name, $data);   // no type check (bug)
    header("Content-Type: application/json");
    echo json_encode(["saved" => "/uploads/" . $name]);
    exit;
}
header("Content-Type: text/plain");
echo "Cockpit CMS. POST a file to /api/assets/upload?name=<filename>\n";
