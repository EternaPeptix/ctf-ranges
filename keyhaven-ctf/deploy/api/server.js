// ===========================================================================
//  Keyhaven internal API  —  api.corp.keyhaven.example
//
//  Three faithful, deep vulnerabilities:
//
//   * CVE-2018-0114 (node-jose JWK header injection): the JWT verifier trusts
//     the public key embedded in the token's own protected header (`jwk`). An
//     attacker supplies their own key as `jwk`, signs with the matching private
//     key, and the server verifies against the attacker-chosen key.  -> stage 3
//
//   * CVE-2016-2107 (CBC padding oracle): the capability-token "open" endpoint
//     decrypts AES-CBC and returns DISTINGUISHABLE errors for bad padding vs
//     bad MAC, giving a padding oracle that decrypts a sealed blob.  -> stage 4
//
//   * CVE-2019-10744 (lodash defaultsDeep prototype pollution): the config
//     merge endpoint runs _.defaultsDeep(config, body); a crafted
//     {"constructor":{"prototype":{...}}} pollutes Object.prototype and flips a
//     server-side default flag on.  -> stage 5
//
//  Isolated training range — do not deploy.
// ===========================================================================
import express from 'express';
import crypto from 'crypto';
import _ from 'lodash';
import { generateKeyPair, exportJWK, importJWK, SignJWT, jwtVerify, decodeProtectedHeader } from 'jose';

const FLAG3 = 'KH{n0de_j0se_jwk_h3ad3r_1nj3ct10n_s3lf_s1gn3d}';
const FLAG4 = 'KH{cbc_padd1ng_0racl3_mac_vs_pad_d1st1ngu1sh}';
const FLAG5 = 'KH{l0dash_def4ultsd33p_pr0t0typ3_p0llut10n}';

const app = express();
app.use(express.json({ limit: '256kb' }));
app.use(express.text({ type: ['text/*', 'application/yaml', 'application/x-yaml'], limit: '256kb' }));

// ---- server JWT signing key (legit tokens) --------------------------------
let SERVER_PRIV, SERVER_PUB_JWK, SERVER_PUB;
async function initKeys() {
  const { publicKey, privateKey } = await generateKeyPair('RS256');
  SERVER_PRIV = privateKey; SERVER_PUB = publicKey;
  SERVER_PUB_JWK = await exportJWK(publicKey);
  SERVER_PUB_JWK.kid = 'keyhaven-sso-2025'; SERVER_PUB_JWK.alg = 'RS256';
}

// ---- STAGE 3: the vulnerable verify (trusts header.jwk) --------------------
async function verifyToken(token) {
  const header = decodeProtectedHeader(token);
  let key;
  if (header.jwk) {
    // CVE-2018-0114: trust the key embedded in the token header.
    key = await importJWK(header.jwk, header.alg);
  } else {
    key = SERVER_PUB; // legitimate path: the server's own key
  }
  const { payload } = await jwtVerify(token, key, { algorithms: [header.alg] });
  return payload;
}

// ---- STAGE 4: AES-CBC capability sealing + padding/MAC oracle --------------
const AES_KEY = crypto.randomBytes(16);
const MAC_KEY = crypto.randomBytes(32);
function pkcs7pad(buf, bs = 16) { const n = bs - (buf.length % bs); return Buffer.concat([buf, Buffer.alloc(n, n)]); }
function pkcs7unpad(buf, bs = 16) {
  const n = buf[buf.length - 1];
  if (n < 1 || n > bs || n > buf.length) throw new Error('pad');
  for (let i = 0; i < n; i++) if (buf[buf.length - 1 - i] !== n) throw new Error('pad');
  return buf.subarray(0, buf.length - n);
}
function seal(ptStr) {
  const P = Buffer.from(ptStr, 'utf8');
  const mac = crypto.createHmac('sha256', MAC_KEY).update(P).digest();
  const blob = pkcs7pad(Buffer.concat([P, mac]));
  const iv = crypto.randomBytes(16);
  const c = crypto.createCipheriv('aes-128-cbc', AES_KEY, iv); c.setAutoPadding(false);
  const ct = Buffer.concat([c.update(blob), c.final()]);
  return Buffer.concat([iv, ct]);
}
// returns 'padding' | 'mac' | 'ok' — an ORACLE; never returns the plaintext.
function openCap(blob) {
  if (blob.length < 32 || blob.length % 16 !== 0) return 'padding';
  const iv = blob.subarray(0, 16), ct = blob.subarray(16);
  let pt;
  try { const d = crypto.createDecipheriv('aes-128-cbc', AES_KEY, iv); d.setAutoPadding(false); pt = Buffer.concat([d.update(ct), d.final()]); }
  catch (e) { return 'padding'; }
  let unp;
  try { unp = pkcs7unpad(pt); } catch (e) { return 'padding'; }
  if (unp.length < 32) return 'mac';
  const P = unp.subarray(0, unp.length - 32), mac = unp.subarray(unp.length - 32);
  const exp = crypto.createHmac('sha256', MAC_KEY).update(P).digest();
  if (mac.length !== exp.length || !crypto.timingSafeEqual(mac, exp)) return 'mac';
  return 'ok';
}
const SEALED = seal(`${FLAG4} | next: pollute /config/update then GET /admin/features`);

// ---- STAGE 5: lodash prototype pollution + a default-flag read -------------
const CONFIG = { theme: 'dark', pageSize: 25 };           // note: no yamlImportEnabled key
function featureEnabled(name) { const opts = {}; return opts[name] === true; } // reads via prototype

// ===========================================================================
app.get('/', (_req, res) => res.type('text').send(
  'Keyhaven internal API · api.corp.keyhaven.example\n' +
  'GET /token (guest JWT) · GET /admin (Bearer) · GET /capability/sealed · POST /capability/open\n'));

app.get('/token', async (_req, res) => {
  const t = await new SignJWT({ scope: 'guest', sub: 'guest@keyhaven.example' })
    .setProtectedHeader({ alg: 'RS256', kid: SERVER_PUB_JWK.kid })
    .setIssuedAt().setExpirationTime('1h').sign(SERVER_PRIV);
  res.json({ token: t, hint: 'the server key id is ' + SERVER_PUB_JWK.kid });
});

app.get('/admin', async (req, res) => {
  const auth = req.headers.authorization || '';
  const token = auth.replace(/^Bearer\s+/i, '');
  if (!token) return res.status(401).json({ error: 'Bearer token required' });
  let payload;
  try { payload = await verifyToken(token); }
  catch (e) { return res.status(401).json({ error: 'token verification failed' }); }
  if (['admin', 'service', 'root'].includes(payload.scope)) {
    return res.type('text').send(
      `admin access granted (scope=${payload.scope}, sub=${payload.sub})\n` +
      `ctf_flag_3=${FLAG3}\n` +
      `next: capability tokens are AES-CBC sealed. GET /capability/sealed and use the\n` +
      `padding/MAC oracle at POST /capability/open (CVE-2016-2107) to recover it.\n`);
  }
  res.status(403).json({ error: `scope ${payload.scope} is not privileged` });
});

app.get('/capability/sealed', (_req, res) =>
  res.json({ sealed: SEALED.toString('base64'),
             hint: 'base64(IV||ciphertext); recover the plaintext via the oracle at /capability/open' }));

app.post('/capability/open', (req, res) => {
  let blob;
  try { blob = Buffer.from((req.body && req.body.token) || '', 'base64'); }
  catch (e) { return res.status(400).json({ error: 'token must be base64' }); }
  const r = openCap(blob);
  if (r === 'padding') return res.status(400).json({ error: 'invalid padding' });
  if (r === 'mac') return res.status(400).json({ error: 'invalid mac' });
  return res.status(200).json({ status: 'capability accepted' });
});

app.post('/config/update', (req, res) => {
  // CVE-2019-10744: defaultsDeep merges attacker keys incl. constructor.prototype
  _.defaultsDeep(CONFIG, req.body || {});
  res.json({ ok: true, config: { theme: CONFIG.theme, pageSize: CONFIG.pageSize } });
});

app.get('/admin/features', (_req, res) => {
  if (featureEnabled('yamlImportEnabled')) {
    return res.type('text').send(
      'feature yamlImportEnabled = true (polluted default)\n' +
      `ctf_flag_5=${FLAG5}\n` +
      'next: POST a YAML document to /config/import — it is forwarded to\n' +
      'vault.corp.keyhaven.example which parses it with PyYAML full_load (CVE-2020-14343).\n');
  }
  res.json({ yamlImportEnabled: false });
});

app.post('/config/import', async (req, res) => {
  if (!featureEnabled('yamlImportEnabled'))
    return res.status(403).json({ error: 'yaml import is disabled' });
  // forward raw YAML to the vault importer
  try {
    const r = await fetch('http://vault.corp.keyhaven.example/import', {
      method: 'POST', headers: { 'Content-Type': 'application/yaml' },
      body: typeof req.body === 'string' ? req.body : JSON.stringify(req.body),
    });
    res.status(r.status).type('text').send(await r.text());
  } catch (e) { res.status(502).json({ error: 'vault unreachable' }); }
});

initKeys().then(() => app.listen(80, () => console.log('[api] listening on :80')));
