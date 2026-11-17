# Obscura — "Provably secure. Allegedly."

> Difficulty: **Very hard** · Category: Crypto / Web / RE · Flags: 5
> Everything here is an isolated lab. Only attack the Obscura widgets.

## Scenario

**Obscura** is a boutique security vendor that builds everything in-house and is
very proud of the math. Five flagship widgets, each one *sound-looking* — the
primitives are real, the code does what it says. None of these flaws is a known
CVE; there is no write-up to find. Each widget dies to exactly one original
insight: brutal to see black-box, a handful of lines once you have it.

Solve in any order. The board is at `http://localhost:8600/`.

## The widgets

| # | Port | Widget | Claims to do |
|---|------|--------|--------------|
| 1 | 8601 | **reverb** | Schnorr signatures with "reproducible" deterministic nonces |
| 2 | 8602 | **echo**   | passwordless login by zero-knowledge proof of identity |
| 3 | 8603 | **warden** | HMAC-signed, scoped download links |
| 4 | 8604 | **tally**  | one-time "sealed envelope" encryption |
| 5 | 8605 | **cage**   | a verified sandbox for untrusted bytecode "formulas" |

Flag format: `FLAG{...}`. There are 5. Nothing here needs brute force or hours of
fuzzing — each flag is one technique, correctly derived.

## cage (c5) — the bytecode ISA

You will need the instruction set. 1-byte opcodes; `PUSH` and `JMP` each carry a
1-byte immediate that follows the opcode:

```
0x00 HALT              stop
0x01 PUSH imm          push imm (0..255)
0x02 ADD               a,b -> (a+b) & 0xff
0x03 XOR               a,b -> a ^ b
0x04 OUT               pop -> append to output
0x10 JMP imm           pc <- imm            (absolute byte offset)
0x20 READFLAG          append the flag to output   (the verifier blocks this)
```

`POST /run {"program":"<hex>"}` verifies, then executes. The verifier rejects any
program that uses `READFLAG`. Your job is to make the VM run `READFLAG` anyway.

## Hints (one per flag — open only if stuck)

<details><summary>1 — reverb</summary>
"Reproducible" nonces: <code>k_i = seed · r^i mod q</code>, with <code>r</code> published and the
counter <code>i</code> returned to you. Write out what one signature equation looks like
once you substitute that nonce. How many unknowns are left across the whole key?
Two signatures, two equations…
</details>

<details><summary>2 — echo</summary>
Non-interactive Schnorr: the verifier recomputes the challenge <code>e</code> itself and
checks <code>g^z == t · Y^e</code>. Look <em>exactly</em> at what goes into <code>e</code>. If <code>e</code> does
not depend on your commitment <code>t</code>, you may choose things in a convenient order:
pick <code>z</code> first, then solve for the <code>t</code> that makes the equation true.
</details>

<details><summary>3 — warden</summary>
A token is only issued for a path that <em>starts with</em> <code>/public/</code>, and the token
signs that exact string. But the fetcher has to turn that string into a file at
some point — does it URL-decode and collapse <code>..</code> <em>before</em> or <em>after</em> the
prefix was checked and signed? What literal string both starts with <code>/public/</code>
and later resolves somewhere else?
</details>

<details><summary>4 — tally</summary>
Seal the same bytes under two different labels and compare. Now seal under labels
of different <em>lengths</em>. What is the keystream actually keyed on? The admin
envelope's label is <code>admin</code>. A one-time pad used twice is not one-time.
</details>

<details><summary>5 — cage</summary>
The verifier reads the program as one linear pass from offset 0, decoding
instruction-by-instruction, and it checks that every <code>JMP</code> target is in-bounds —
but not that the target is an instruction boundary it actually visited. The VM,
though, will set the program counter to the exact byte you name. A byte can be an
immediate to the verifier and an opcode to the VM.
</details>

## Scope / legal

Intentionally vulnerable training widgets with intentional "secrets" (test keys).
Run only on an isolated host you control. Do not deploy, and do not point these
techniques at systems you are not authorized to test.
