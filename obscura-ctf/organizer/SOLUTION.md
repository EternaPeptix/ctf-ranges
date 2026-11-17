# Obscura — full walkthrough

Every widget is sound-*looking*; each has one original design flaw. Reference
exploit for all five is `scripts/solve.py` (pure stdlib, in-network).

The two crypto widgets share one group (`app/common.py`): the RFC 3526 2048-bit
MODP **safe prime** `p`, with `q = (p−1)/2` prime and `g = 4` a generator of the
order-`q` subgroup of quadratic residues. All exponents are mod `q`.

---

## c1 — reverb · deterministic nonces are linearly dependent

**Scheme.** Textbook Schnorr. Key `d`, public `Y=g^d`. To sign `m`: nonce `k`,
`R=g^k`, `e=H(R‖m) mod q`, `s=k+e·d mod q`; signature `(e,s)`; verify
`H(g^s·Y^(−e) ‖ m) == e`. `/sign` is an oracle for every message *except*
`grant-admin`; `/admin` runs the command iff a valid signature on `grant-admin`
is presented.

**The "feature" that kills it.** For reproducibility the appliance derives the
nonce deterministically from one secret `seed` and a **public** ratio `r`:

```
k_i = seed · r^i   (mod q)     with i the per-signature counter, returned to you
```

**Attack.** Substitute the nonce into the signing equation:

```
s_i = k_i + e_i·d = seed·r^i + e_i·d        (mod q)
```

`r`, `i`, `e_i`, `s_i` are all known; only `seed` and `d` are unknown — two
unknowns, and every signature is one linear equation in them. Take two:

```
[ r^{i0}  e0 ] [ seed ]   [ s0 ]
[ r^{i1}  e1 ] [  d   ] = [ s1 ]   (mod q)
```

`q` is prime, so invert the 2×2 and read off `d`. Then forge a normal Schnorr
signature on `grant-admin` with any nonce you like and POST it.

```
d = (a0·s1 − a1·s0)·det^{-1} mod q,  det = a0·e1 − a1·e0,  a_i = r^{i_i}
```

**Lesson.** "Deterministic/reproducible" nonces that are a *public* function of a
per-key secret make the nonces linearly related, and linear relations among
Schnorr nonces are fatal — one extra signature and the key falls out. (Contrast
with RFC 6979, where the nonce is a PRF of the key *and the message* and no such
public algebraic relation exists.)

---

## c2 — echo · Fiat–Shamir that forgets the commitment

**Scheme.** Prove knowledge of the admin discrete log `x` (`Y=g^x`) with a Schnorr
identification, made non-interactive by Fiat–Shamir. The server recomputes the
challenge and checks `g^z == t·Y^e`, where

```
e = H(Y ‖ nonce)          # the bug: t is NOT in the hash
```

**Attack.** A sound Fiat–Shamir challenge must commit to `t` (`e=H(Y‖t‖nonce)`).
Because `e` here is independent of `t`, you can fix the transcript in a convenient
order. Fetch a nonce, compute `e`, choose any `z`, and **back-solve the
commitment**:

```
t = g^z · Y^(−e)   (mod p)
```

Now `t·Y^e = g^z·Y^(−e)·Y^e = g^z`, so the check passes — a valid proof produced
with only the public key `Y`. No knowledge of `x` anywhere.

**Lesson.** The Fiat–Shamir transform is only sound if the hash binds the prover's
commitment. Omitting `t` turns a proof of knowledge into a proof of nothing: it is
universally forgeable from public data alone.

---

## c3 — warden · authorize/sign *before* decode + normalize

**Scheme.** `/token?path=…` issues `HMAC(path)` **iff** `path` starts with
`/public/`. `/fetch?path=…&token=…` verifies the HMAC over `path`, then
URL-decodes it, normalizes `..`, joins under `/data`, and returns the file.

**Attack.** Both the authorization check and the signature operate on the **raw,
still-percent-encoded** string; decoding and normalization happen only at fetch
time. Pick

```
/public/%2e%2e/admin/flag.txt
```

It *literally starts with* `/public/`, so a token is issued and signs it verbatim.
At fetch the same string verifies, then decodes to `/public/../admin/flag.txt` and
normalizes to `/admin/flag.txt` — outside `/public/`, straight to the flag.

**Lesson.** Canonicalize **before** you authorize and sign, never after. "Starts
with `/public/`" on an un-decoded, un-normalized path is not a containment check;
it's a suggestion.

---

## c4 — tally · a one-time pad used more than once

**Scheme.** `ct = pt XOR keystream(label)`, where
`keystream(label) = SHA256(master ‖ len(label) ‖ counter) …`. The admin envelope
(`/admin`) is the flag sealed under label `admin`.

**Attack.** The KDF mixes in only **`len(label)`**, not the label bytes — so every
label of the same length yields the *same* keystream. `admin` has length 5. Seal a
**known** plaintext of the admin ciphertext's length under any 5-char label; with
`pt = 00…00` the returned ciphertext *is* the keystream. XOR it against the admin
ciphertext:

```
KS      = seal("xxxxx", 00…00)
flag    = admin_ct XOR KS
```

**Lesson.** Keystream reuse = two-time pad = no secrecy. A nonce/label must
actually enter the key derivation in full; keying on a coarse feature like length
silently collapses many "unique" streams into one.

---

## c5 — cage · the verifier and the VM disagree on where instructions start

**Scheme.** A static verifier linearly disassembles the bytecode from offset 0,
rejecting any program that decodes `READFLAG (0x20)` or an unknown opcode, and
checking that every `JMP` immediate is in-bounds. Verified programs run on a stack
VM.

**Attack.** The verifier checks jump **bounds** but not jump **alignment** — it
never confirms a target is an offset its linear scan actually treated as an
instruction start. The VM sets `pc` to the exact target. So hide the forbidden
opcode as an immediate and jump onto it:

```
offset: 0  1  2  3
bytes : 01 20 10 01
        └PUSH 0x20┘ └JMP 1┘
```

- **Verifier** scans: `00:PUSH imm=0x20` (the `0x20` is data, not an opcode),
  `02:JMP 1` (target 1 is in-bounds). No `READFLAG` seen → **accepted**.
- **VM** runs: `PUSH 0x20` → `JMP 1` sets `pc=1` → byte `0x20` decodes as
  `READFLAG` → the flag is emitted.

`POST /run {"program":"01201001"}` returns the flag in `output`.

**Lesson.** A bytecode verifier must model control flow the same way the
interpreter does — including that jumps can land mid-instruction in a
variable-length ISA. Verifying a single linear decoding while the runtime allows
arbitrary re-entry is the classic overlapping-instruction blind spot.

---

## Reproduce

```bash
make up
make check     # scripts/solve.py in a throwaway container on obscura_net; exit 0
make down
```

Keys are random per boot; the exploits recover or sidestep them every run, so
`make reset && make check` stays green.
