<?php
/* c12 — CVE-2026-70554 : MaxSite CMS passes the `maxsite_comuser` cookie to
 * unserialize() with no class allow-list -> PHP object injection / POP chain.
 * A gadget class present in the app reads a file in __wakeup(). */

class CommentUser {
    public $name = "guest";
    public $email = "";
}

// gadget: on wake-up it renders a "cached template" by reading a path
class TemplateCache {
    public $template = "";
    public function __wakeup() {
        if ($this->template) {
            echo file_get_contents($this->template);
        }
    }
}

$cookie = $_COOKIE["maxsite_comuser"] ?? "";
header("Content-Type: text/plain");
if ($cookie === "") {
    echo "MaxSite CMS. Returning commenters are remembered via the maxsite_comuser cookie.\n";
    exit;
}
$user = unserialize(base64_decode($cookie));   // BUG: untrusted deserialization, no allow-list
echo "\nwelcome back" . (is_object($user) && isset($user->name) ? ", " . $user->name : "") . "\n";
