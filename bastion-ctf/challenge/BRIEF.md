# Military-grade security — Bastion

> Difficulty: **Hard** · Category: Web / Crypto · Flags: 5
> Everything here is an isolated lab. Only attack the Bastion app.

## Scenario

**Bastion** sells "military-grade" document custody and will tell you, at length,
how secure it is. It signs every request, encrypts every session, and exposes
almost nothing. There is no `.git`, no debug endpoint, no backup in the webroot.

And yet. Five times, something that looks completely solid has a single thread
you can pull — invisible unless you know exactly what you're looking at, and
trivial the moment you do.

## Rules of engagement

- **Start here:** `http://localhost:8080/`
- Flag format: `BAS{...}`. There are 5.
- Nothing here needs brute force or hours of fuzzing. Each flag is one technique.

## Hints (one per flag — open only if stuck)

<details><summary>1</summary>
Save the landing page and look at its <em>bytes</em>, not its pixels. Is the
rendered text the same length as the source? Some characters have no width.
</details>

<details><summary>2</summary>
`admin` is reserved. But "reserved" and "is an admin" may be decided by two
different notions of equality. What does `unicodedata.normalize('NFKC', x)` do
to letters that aren't ASCII but <em>look</em> (to the normalizer) like they are?
</details>

<details><summary>3</summary>
Decode your session token. Its length is a multiple of 16, and if you register
two names with a repeated 16-byte chunk, the token repeats too. Same plaintext
block → same ciphertext block means one mode in particular. You control part of
the plaintext; you can rearrange blocks. (Cryptopals challenge 13.)
</details>

<details><summary>4</summary>
`GET /api/report` tells you the signature is `md5(secret ‖ data)` and hands you a
valid `(data, sig)` pair. You don't need the secret to append to a message hashed
that way — you only need its length, and you can guess that.
</details>

<details><summary>5</summary>
`/api/preview` only fetches URLs "within bastion.internal". *Within*, checked how?
If the check is a substring search rather than an anchored match, a URL can both
point somewhere else and still contain that string. Where does the app say its
internal diagnostics live?
</details>

## Scope / legal

Intentionally vulnerable training app. Run it only on a host you control, on an
isolated network. Do not point these techniques at systems you are not
authorized to test.
