# Flags (organizer)

All verified live end-to-end via `scripts/verify.sh` (RESULT: ALL 7 CORE FLAGS
CAPTURED, exit 0), driven through the real smuggle → SAML → gateway path.

| # | Flag | CVE | How to get it |
|---|------|-----|---------------|
| 1 | `KH{t3_cl_d3sync_smuggl3d_past_th3_edg3_acl}` | CVE-2019-18277 | smuggle a request past the edge ACL to `/internal/bootstrap` |
| 2 | `KH{saml_xsw_s1gn3d_0n3_assert10n_tru5t3d_an0th3r}` | CVE-2018-0489 | XSW-wrap the signed guest assertion with an admin one; POST to `/internal/saml/acs` |
| 3 | `KH{n0de_j0se_jwk_h3ad3r_1nj3ct10n_s3lf_s1gn3d}` | CVE-2018-0114 | forge a JWT with your own key in the `jwk` header; `GET /gw/api/admin` |
| 4 | `KH{cbc_padd1ng_0racl3_mac_vs_pad_d1st1ngu1sh}` | CVE-2016-2107 | padding-oracle the sealed capability via `POST /gw/api/capability/open` |
| 5 | `KH{l0dash_def4ultsd33p_pr0t0typ3_p0llut10n}` | CVE-2019-10744 | pollute `yamlImportEnabled` via `POST /gw/api/config/update`; `GET /gw/api/admin/features` |
| 6 | `KH{pyyaml_full_l0ad_typ3_ext3nd_3x3c_byp4ss}` | CVE-2020-14343 | POST the `type`/`extend`/`exec` YAML gadget to `/gw/api/config/import` |
| 7 | `KH{putty_b1as3d_n0nce_hnp_latt1ce_k3y_r3c0v3ry}` | CVE-2024-31497 | collect biased sigs from `/gw/signer/sign`, HNP-lattice the key, sign the challenge, `POST /gw/signer/forge` |
| B | `KH{ecdsa_psych1c_s1gnatur3_z3r0_z3r0_4ccept3d}` | CVE-2022-21449 | `POST /gw/signer/verify-manifest` with `{"r":0,"s":0}` |

## Gating / dependencies
- Stages 3–7 require the `kh_corp` cookie, issued **only** by a successful SAML
  admin login (stage 2), which is reachable **only** by smuggling (stage 1).
- Stage 6 requires the `yamlImportEnabled` flag to be polluted first (stage 5).
- Stage 7's `/forge` and `/verify-manifest` accept a signature over the privileged
  manifest; `/sign` refuses to sign `root`/challenge messages, so the key must be
  recovered, not borrowed.

## Difficulty / scoring suggestion

| Stage | 1 | 2 | 3 | 4 | 5 | 6 | 7 | Bonus |
|-------|---|---|---|---|---|---|---|-------|
| Points | 250 | 400 | 350 | 400 | 300 | 350 | 600 | 200 |

Expect a strong solo player **8–16h**; stage 7 (lattice) and stage 2 (XSW) are
the long poles. First-blood bonus optional.

## Decoys / discipline
- Stage 2: tampering the *signed* assertion (not wrapping) fails with a digest
  mismatch — the signature really protects its content.
- Stage 3: a legitimately-issued guest token is rejected at `/gw/api/admin` (403);
  only a forged elevated-scope token works.
- Stage 7: resetting/guessing is useless — only a real signature over the exact
  challenge string is accepted.
