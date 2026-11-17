# carillon -- solution (spoilers)

## The idea in one paragraph

The manual says any command code not in the table stops the machine. That is
true for 239 of the 240 unlisted codes. The remaining one, drawn at startup,
does not stop the machine: it releases the drawer catch for the rest of that
run, after which the drawer cells `0xC0..0xDF` read back their real contents
(the token) instead of 0. The manual gives no hint of this, so the only way to
learn which code it is, is to run the unlisted codes and notice the one that
behaves differently.

## Which code is special

It is **not fixed**. `app/serve.py` draws it with `secrets.choice` from the 240
unlisted codes every time the process starts, together with a fresh token:

```
UNLISTED = [code for code in range(256) if code not in BY_CODE]
SPECIAL  = secrets.choice(UNLISTED)
TOKEN    = ("FLAG{" + secrets.token_hex(13) + "}").encode("ascii")   # 32 bytes
```

Listed codes (never special): `0x10`–`0x18`, `0x20`, `0x21`, `0x30`,
`0x40`–`0x42`, `0x4F`. Every other byte value is a candidate.

To see what the running instance drew:

- `make check` prints it: `[solve] special command: 0x..`
- the container log has it (organizer-only, never served over HTTP):
  `docker logs car-app | head -1` ->
  `[carillon] organizer: special command 0x.., token FLAG{...}`

## Method

### 1. Read the manual

`GET /` gives everything needed to assemble programs:

- `commands[]`: `code`, `name`, `operands[]` (each `{name, kind}`), `effect`.
  The four that matter are `SET x n` (`0x11`), `READ x y` (`0x20`),
  `PLAY x` (`0x30`) and `STOP` (`0x4F`).
- `registers.ids`: `A`=0, `B`=1, `C`=2, `D`=3.
- `memory.regions[]`: the one with `"access": "locked"` is the drawer,
  `start` 192 (`0xC0`), `size` 32.
- The listed codes are the `code` values; the unlisted set is the other 240
  byte values.

### 2. Try the unlisted codes

A probe that reads one drawer cell and plays it:

```
SET B,0xC0     11 01 c0
READ A,B       20 00 01
PLAY A         30 00
STOP           4f
```

On its own this outputs `00`: the drawer is locked. Now put each unlisted code
in front of it and run `<code> 11 01 c0 20 00 01 30 00 4f`:

- an ordinary unlisted code: `output ""`, `steps 0`,
  `reason "unknown command 0x.. at position 0"`.
- the special code: `output "46"` (`F`, the first token byte), `steps 5`,
  `reason null`.

That is at most 240 runs, and exactly one stands out. Two independent signals
mark it: the machine did not stop on the code, and the drawer read returned
real data.

### 3. Open the drawer and read it out

The catch is released only for the run that executes the special code, so the
final program starts with it. Straight-line version (what `solve.py` sends,
258 bytes, 98 steps):

```
<special>
SET B,0xC0 / READ A,B / PLAY A
SET B,0xC1 / READ A,B / PLAY A
...
SET B,0xDF / READ A,B / PLAY A
STOP
```

The same thing as a loop inside the machine (20 bytes, 164 steps):

```
pos  bytes       command
 0   <special>
 1   11 01 c0    SET B,0xC0      address
 4   11 02 20    SET C,32        cells left
 7   20 00 01    READ A,B        <- loop
10   30 00       PLAY A
12   17 01       INC B
14   18 02       DEC C
16   42 02 07    JNZ C,7
19   4f          STOP
```

The 32 output bytes are the token, `FLAG{` + 26 hex digits + `}`.

### 4. Reference solver

`scripts/solve.py` does exactly steps 1 to 3 over HTTP and prints
`TOKEN: FLAG{...}`. It has no knowledge of the special code: it sweeps all 240
unlisted codes, insists that exactly one opens the drawer, and uses that one.

## Why there is no other way

- The token is never copied into the machine's memory. `Box.cell()` returns
  `TOKEN[addr - 0xC0]` only while `catch_released` is true; otherwise drawer
  addresses read 0. `WRITE` only reaches the roll.
- `catch_released` is set in exactly one place: the branch of `Box.step()`
  that handles the special code. No listed command touches it.
- Every run builds a new `Box`, so nothing carries over between runs.
- `GET /` is built from the listed table only; neither the special code nor
  the token appears in it, and it never says the drawer can be opened.

## Checks

```
make up && make check             # PASS, prints the special code and the token
make reset && make check          # new special code, new token, PASS again
```

`make check` takes a couple of seconds (242 `/run` requests).
