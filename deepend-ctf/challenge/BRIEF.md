# The Deep End

> Difficulty: **Hard / research-grade** · Category: Web · Protocol · Crypto · Pwn
> Flags: 6 · Everything here is an isolated lab. Only attack the Deep End hosts.

## Scenario

Six services, six vulnerabilities disclosed in the back half of 2026. None of
them is a one-request bug. Each is a *technique* — a parser disagreeing with
itself, a signature scheme that forgot to bind a value, a cipher used twice, a
sandbox that trusted the wrong accessor, two readers of one file that read
different things. Recognise the technique and the exploit is short. Don't, and
you'll stare at a wall.

## Rules of engagement

- **Scoreboard:** `http://localhost:8400/` — the board + where you submit flags.
- **Challenges:** `http://localhost:8401` … `8406`. #1 wants a hand-crafted
  request line; #6 wants a hand-crafted file.
- Flag format: `0DAY{...}`.

## The board

| Port | Theme | Product |
|------|-------|---------|
| 8401 | a proxy that routes and forwards differently | Traefik |
| 8402 | a signature that covers a different name than the one you're processed as | Keycloak SAML |
| 8403 | a signature you can make without the key | adaptor signatures |
| 8404 | a cipher that reused something it shouldn't | AES-GCM |
| 8405 | a "safe" template feature that isn't | RestrictedPython |
| 8406 | an archive that says one thing and does another | Rust zip2 |

## General hints

- **8401:** how does the backend see your request target vs how the edge ACL sees
  it? What does Go do with a request-target that isn't a normal path?
- **8402:** the server decodes parameter *names*. The signature does not.
- **8403:** read the verification equation. What is actually checked about `r`?
- **8404:** the nonce never changes. Two messages under one (key, nonce) is a
  textbook break — look up the "forbidden attack."
- **8405:** `str.format` can walk attributes. Where does `__init__.__globals__`
  lead?
- **8406:** a zip has two copies of each filename. Make them disagree.

## Scope / legal

Intentionally vulnerable re-implementations of real, disclosed H2-2026 CVEs. Run
only on a host you control, on an isolated network. Do not point these techniques
at systems you are not authorized to test.
