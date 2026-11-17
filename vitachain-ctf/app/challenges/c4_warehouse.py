"""c4 — warehouse : "Import a product image by URL."

Based on H1 #1369312 (Concrete CMS — SSRF to AWS IMDS via DNS rebinding) and
H1 #632101 (GitLab — SSRF protections bypassed by DNS rebinding). VitaChain's
warehouse lets a seller import a product photo from any URL; the server fetches
it so the browser never touches the remote host.

The importer does everything an SSRF filter is "supposed" to do:
  * resolves the URL's host and REJECTS anything that is not a public IP
  * blocks the link-local metadata address 169.254.169.254 and every static
    bypass for it — 127.*, 10.*, 192.168.*, 172.16-31.*, 0.0.0.0, decimal /
    octal / hex integer IP encodings, IPv6 (::1, ::ffff:169.254.169.254,
    fd00::/8 ULAs) and the internal service names (imds, localhost, metadata…)
  * refuses to follow redirects, so a 302->internal is not a way in

...and the static validator genuinely holds: there is no single-URL string that
slips a private address past it.

Flaw (real): the importer resolves the host TWICE — once to validate (TOCTOU
time-of-check) and once to connect (time-of-use) — and trusts that the two
lookups agree. With TTL 0 the attacker's DNS answers the public IP on the first
lookup (which passes validation) and flips to the internal metadata host on the
second lookup (which is what actually gets fetched). The check and the use see
different addresses; the public IP is validated, the IMDS host is dialed, and
the role's `SecretAccessKey` (the flag) walks straight back out in the body.
"""
import ipaddress
import urllib.parse
import urllib.request
from flask import Flask, request, jsonify, Response

# NOTE: this module deliberately defines NO FLAG. The secret is the IAM
# credential served by the separate `imds` container; it is captured only by
# actually reaching that host through the rebind, never from this process.

app = Flask(__name__)

_UA = "VitaChain-ImageImporter/1.0"
_PUBLIC_DEFAULT = "93.184.216.34"          # what an unknown public name resolves to

# Host names that must never be dialed, regardless of what they resolve to.
_BLOCKED_NAMES = {
    "imds", "localhost", "metadata", "metadata.google.internal",
    "metadata.goog", "instance-data", "ip6-localhost", "ip6-loopback",
}
_BLOCKED_SUFFIXES = (".internal", ".local", ".localhost")

# Attacker-controlled DNS. host -> {"answers": [...], "i": <calls so far>}.
# Each resolve() walks the answer list by one; the final entry repeats. TTL 0.
_DNS = {}


# --------------------------------------------------------------------------- #
# resolver (models attacker-controlled DNS with per-host flip, TTL 0)
# --------------------------------------------------------------------------- #
def _looks_like_ip(h):
    try:
        ipaddress.ip_address(h)
        return True
    except ValueError:
        return False


def resolve(host):
    """In-app stub resolver.

    A registered host walks its answer list on every call (the last entry
    repeats forever), so lookup #1 and lookup #2 can return different answers —
    that difference IS the DNS-rebind primitive. A non-registered literal IP
    resolves to itself; any other non-registered name resolves to a fixed
    public IP.
    """
    h = (host or "").strip().lower().rstrip(".")
    rec = _DNS.get(h)
    if rec:
        i = rec["i"]
        ans = rec["answers"][i] if i < len(rec["answers"]) else rec["answers"][-1]
        rec["i"] = i + 1
        return ans
    if _looks_like_ip(h):
        return h
    return _PUBLIC_DEFAULT


# --------------------------------------------------------------------------- #
# the SSRF validator — genuinely blocks every static bypass
# --------------------------------------------------------------------------- #
def _c_int(s):
    """Parse one host label as a C-style integer (hex 0x…, octal 0…, decimal).
    Raises ValueError for anything that is not purely such an integer."""
    s = s.strip()
    if s == "":
        raise ValueError("empty label")
    low = s.lower()
    if low.startswith("0x"):
        return int(low, 16)
    if s.startswith("0") and len(s) > 1:
        return int(s, 8)
    return int(s, 10)


def _inet_aton_like(host):
    """Decode decimal / octal / hex and short-dotted IPv4 forms the way
    inet_aton (and most HTTP stacks) do, so the validator sees the SAME address
    a naive socket would dial. Returns an IPv4Address or None."""
    parts = host.split(".")
    if not 1 <= len(parts) <= 4:
        return None
    try:
        nums = [_c_int(p) for p in parts]
    except ValueError:
        return None
    if any(n < 0 for n in nums):
        return None
    n = len(nums)
    if n == 1:
        val = nums[0]
        if val > 0xFFFFFFFF:
            return None
    elif n == 2:          # a.b   -> b fills the low 24 bits
        a, b = nums
        if a > 0xFF or b > 0xFFFFFF:
            return None
        val = (a << 24) | b
    elif n == 3:          # a.b.c -> c fills the low 16 bits
        a, b, c = nums
        if a > 0xFF or b > 0xFF or c > 0xFFFF:
            return None
        val = (a << 24) | (b << 16) | c
    else:                 # a.b.c.d
        if any(x > 0xFF for x in nums):
            return None
        val = (nums[0] << 24) | (nums[1] << 16) | (nums[2] << 8) | nums[3]
    try:
        return ipaddress.IPv4Address(val)
    except ipaddress.AddressValueError:
        return None


def _forbidden(ipobj):
    """True unless ipobj is a genuinely public, globally routable address."""
    if isinstance(ipobj, ipaddress.IPv6Address) and ipobj.ipv4_mapped is not None:
        ipobj = ipobj.ipv4_mapped          # ::ffff:169.254.169.254 -> 169.254.169.254
    return (
        ipobj.is_loopback
        or ipobj.is_link_local
        or ipobj.is_private
        or ipobj.is_reserved
        or ipobj.is_multicast
        or ipobj.is_unspecified
        or not ipobj.is_global
    )


def _host_is_forbidden(host):
    """Catch a host string that *encodes* a non-public address in any syntax
    (dotted, decimal, octal, hex, IPv6, IPv4-mapped IPv6)."""
    candidates = []
    try:
        candidates.append(ipaddress.ip_address(host))
    except ValueError:
        pass
    v4 = _inet_aton_like(host)
    if v4 is not None:
        candidates.append(v4)
    return any(_forbidden(ip) for ip in candidates)


def _validate(host, resolved):
    """Return None if (host, resolved-ip) is safe to fetch, else a reason."""
    h = (host or "").strip().lower().rstrip(".")
    if h in _BLOCKED_NAMES or h.endswith(_BLOCKED_SUFFIXES):
        return "blocked internal host name"
    if _host_is_forbidden(h):
        return "host literal encodes a non-public address"
    try:
        ipobj = ipaddress.ip_address(resolved)
    except ValueError:
        return "resolver did not return a routable IP address"
    if _forbidden(ipobj):
        return "resolved address is private/loopback/link-local/reserved"
    return None


# --------------------------------------------------------------------------- #
# the actual outbound GET (factored out so tests can monkeypatch it)
# --------------------------------------------------------------------------- #
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None                         # never follow a redirect


def _do_get(target, path):
    """Perform the real outbound HTTP GET against the resolved `target`.

    This is the time-of-USE connection: `target` is whatever the second DNS
    lookup returned. In Docker the rebind's second answer is "imds", so this
    reaches http://imds/<path> and returns the IMDS body. Redirects are not
    followed. Kept tiny and at module scope so tests can monkeypatch it.
    """
    if not path.startswith("/"):
        path = "/" + path
    url = "http://%s%s" % (target, path)
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    opener = urllib.request.build_opener(_NoRedirect)
    with opener.open(req, timeout=5) as resp:
        return resp.read().decode("latin1")


# --------------------------------------------------------------------------- #
# routes
# --------------------------------------------------------------------------- #
@app.get("/")
def home():
    return jsonify(
        shop="VitaChain warehouse — product image importer",
        flow="POST /dns/register {host, answers:[...]} -> GET /fetch?url=http://<host>/...",
        endpoints={
            "POST /dns/register {host, answers:[ip|name, ...]}":
                "register attacker DNS: successive resolve() calls walk the answers (TTL 0, last repeats)",
            "GET  /fetch?url=<url>":
                "import a URL server-side: validates the resolved host is public, then fetches and returns the body",
        },
        note="validation and fetch each resolve the host independently — a rebind between the two lookups is the bug.",
    )


@app.post("/dns/register")
def dns_register():
    j = request.get_json(silent=True) or {}
    host = str(j.get("host", "")).strip().lower().rstrip(".")
    answers = j.get("answers", [])
    if not host or not isinstance(answers, list) or not answers:
        return jsonify(error="need {host, answers:[...]} with a non-empty answers list"), 400
    _DNS[host] = {"answers": [str(a) for a in answers], "i": 0}
    return jsonify(
        ok=True, host=host, answers=_DNS[host]["answers"], ttl=0,
        note="successive resolve() calls return successive answers; the last entry repeats",
    )


@app.get("/fetch")
def fetch():
    url = request.args.get("url", "")
    if not url:
        return jsonify(error="missing ?url="), 400
    try:
        parts = urllib.parse.urlsplit(url)
    except ValueError:
        return jsonify(error="unparseable url"), 400
    if parts.scheme not in ("http", "https"):
        return jsonify(error="only http/https URLs may be imported"), 400
    host = parts.hostname
    if not host:
        return jsonify(error="no host in url"), 400

    # --- TIME OF CHECK: resolve #1, then validate -------------------------
    ip1 = resolve(host)
    reason = _validate(host, ip1)
    if reason:
        return jsonify(error="SSRF blocked", host=host, resolved=ip1, reason=reason), 400

    # --- TIME OF USE: resolve #2 (the rebind flip), then connect ----------
    # BUG: a fresh lookup, NOT the validated ip1. With TTL 0 the attacker's
    # DNS has already flipped this host to the internal metadata target.
    ip2 = resolve(host)
    path = parts.path or "/"
    if parts.query:
        path += "?" + parts.query
    try:
        body = _do_get(ip2, path)
    except Exception as e:
        return jsonify(error="fetch failed", target=ip2, detail=str(e)), 502
    return Response(body, mimetype="text/plain")
