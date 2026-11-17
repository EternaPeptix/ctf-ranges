# Flags (organizer)

All verified live via `scripts/solve.py` (RESULT: ALL 5 FLAGS CAPTURED, exit 0).

| # | Flag | Needle | One-liner exploit |
|---|------|--------|-------------------|
| 1 | `BAS{z3r0_w1dth_chars_h1d1ng_1n_pl41n_s1ght}` | zero-width stego | filter `​`/`‌` in `/`, read as bits |
| 2 | `BAS{nfkc_n0rm4liz4t10n_h0m0glyph_4dm1n}` | NFKC vs `lower()` | `POST /api/register {"name":"ᴬdmin"}` |
| 3 | `BAS{ecb_cut_4nd_p4st3_bl0ck_shuffl3}` | AES-ECB cut-and-paste | two registers + splice ciphertext blocks → `GET /vault?token=` |
| 4 | `BAS{md5_l3ngth_3xt3ns10n_f0rg3d_s1gn4tur3}` | MD5 length extension | extend the sample `(data,sig)` with `&admin=1` → `GET /api/report` |
| 5 | `BAS{un4nch0r3d_r3g3x_ssrf_t0_l0c4lh0st}` | unanchored allowlist regex | `GET /api/preview?url=http://127.0.0.1/_internal/flag?x=bastion.internal` |

## Implementation notes
- The ECB key and are random per boot; the signing secret is a fixed 16-byte
  value whose *length* is the only thing C4 needs (the solver brute-forces 1–39).
- `/_internal/flag` is only served to `remote_addr == 127.0.0.1`, so it is
  reachable solely through the SSRF (the app fetching its own loopback).
- Flag 2 relies on `"ᴬ"` (U+1D2C) lowercasing to itself but NFKC-folding to `A`;
  any compatibility homoglyph of A/D/M/I/N works.

## Difficulty / scoring suggestion
These are hard-to-*find* but standard techniques, so reward recognition:
**200 pts each** (flat). A strong player who knows ECB/length-extension cold can
clear it in well under an hour; a learner may need a day and some reading. Good
as a "do you recognize the shape?" board or a crypto-lite warmup.

## Not CVEs
Classic technique challenges (Cryptopals-style), not specific CVE IDs — but each
mirrors real incidents: zero-width exfiltration/watermarks, Unicode
normalization auth bypasses, ECB "ECB penguin"/token forgery, Flickr's 2009 MD5
length-extension API-signing break, and countless `re.search`-without-`$` SSRF
allowlist bypasses.
