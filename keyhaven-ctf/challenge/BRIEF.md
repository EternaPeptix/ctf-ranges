# Null Cipher — Keyhaven

> Difficulty: **Very Hard** · Category: Web / Crypto / Chain · Flags: 7 core + 1 bonus
> Everything here is an isolated lab. Only attack the Keyhaven hosts below.

## Scenario

**Keyhaven** sells "privacy-first" single sign-on and a secure document vault.
Their marketing is all about cryptography — which makes it embarrassing how many
of the hard protocol and crypto details their own stack gets wrong. You have a
black-box assessment of `app.keyhaven.example`.

Objective: get from the public edge all the way to Keyhaven's **master
document-signing key**.

## Rules of engagement

- **Start here:** `http://localhost:8080/` (the edge)
- In scope: the edge and anything you can reach *from it* on the
  `corp.keyhaven.example` network.
- The internal services (`sso`, `api`, `vault`, `signer`) are **not
  internet-facing**. You are expected to reach them the way a real attacker would.
- Flag format: `KH{...}`. Validate before you submit.

## What you're looking for

| # | Roughly where |
|---|---------------|
| 1 | The edge blocks an internal path. Make it forward a request it shouldn't. |
| 2 | A signature that's valid — over something the app never actually reads. |
| 3 | A token that tells the server which key to trust it with. |
| 4 | An endpoint that decrypts and tells you *too much* about why it failed. |
| 5 | A "merge" that reaches somewhere it was never meant to. |
| 6 | A config importer that parses a little too eagerly. |
| 7 | A signer whose randomness isn't. Collect enough and the key falls out. |
| B | A signature that is… nothing at all. |

## Hints (use only if stuck)

<details><summary>Getting in (1–2)</summary>

The edge and its backend are different programs that parse HTTP a little
differently — especially `Transfer-Encoding`. Once you're reaching internal
paths, look at how the SAML consumer decides *which* assertion is you: does it
check the one the signature actually covers?
</details>

<details><summary>The internal API (3–5)</summary>

JWTs here carry everything the verifier needs — maybe too much. The capability
"open" endpoint is chatty about *why* a token is bad. And the config merge is a
lodash `defaultsDeep`; what does it do with a `constructor` key?
</details>

<details><summary>The core (6–7)</summary>

Enabling the YAML importer (stage 5) feeds an old PyYAML; `full_load` is not as
safe as it sounds. For the finale: ECDSA with a nonce that isn't uniformly random
is textbook — the top bits of every nonce are zero. That's a Hidden Number
Problem; a lattice will hand you the private key.
</details>

## Scope / legal

This range re-implements real, disclosed, pre-2026 CVEs for training. It is
intentionally vulnerable. Run it only on a host you control, on an isolated
network. Do not point these techniques at systems you are not authorized to test.
