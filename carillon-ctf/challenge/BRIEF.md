# Carillon No.8

A clockwork music box sits at `http://localhost:9200` (inside the puzzle
network: `http://app`). It runs **programs**. A program is a string of bytes:
a command code, then that command's operand bytes, then the next command code,
and so on. Whatever the program PLAYs comes back as the output.

`GET /` is the box's full manual, as JSON. `POST /run` runs a program on a
fresh box. That is the whole interface.

## The machine

- **Dials.** Four 8-bit registers, `A`, `B`, `C`, `D` (ids 0, 1, 2, 3). All are
  0 at the start of every run. Arithmetic wraps around at 256.
- **Memory.** 256 cells of 8 bits each.

  | cells         | name   | access     | contents                               |
  |---------------|--------|------------|----------------------------------------|
  | `0x00`–`0x7F` | roll   | read/write | scratch; all 0 at the start of a run   |
  | `0x80`–`0x9F` | plate  | read-only  | the maker's plate, ASCII               |
  | `0xA0`–`0xBF` | blank  | read-only  | always 0                               |
  | `0xC0`–`0xDF` | drawer | locked     | a read gives 0, a write does nothing   |
  | `0xE0`–`0xFF` | blank  | read-only  | always 0                               |

- **Commands.** `x` and `y` are dial ids, `n` is a number, `p` is a program
  position. Every operand is one byte.

  | code   | name  | operands | effect                                         |
  |--------|-------|----------|------------------------------------------------|
  | `0x10` | REST  |          | nothing happens                                |
  | `0x11` | SET   | `x n`    | x = n                                          |
  | `0x12` | COPY  | `x y`    | x = y                                          |
  | `0x13` | ADD   | `x y`    | x = (x + y) mod 256                            |
  | `0x14` | SUB   | `x y`    | x = (x - y) mod 256                            |
  | `0x15` | AND   | `x y`    | x = x AND y                                    |
  | `0x16` | XOR   | `x y`    | x = x XOR y                                    |
  | `0x17` | INC   | `x`      | x = (x + 1) mod 256                            |
  | `0x18` | DEC   | `x`      | x = (x - 1) mod 256                            |
  | `0x20` | READ  | `x y`    | x = the cell whose address is on dial y        |
  | `0x21` | WRITE | `x y`    | the cell whose address is on dial x = y (roll only) |
  | `0x30` | PLAY  | `x`      | append the value on dial x to the output       |
  | `0x40` | JUMP  | `p`      | continue at position p                         |
  | `0x41` | JZ    | `x p`    | if x is 0, continue at position p              |
  | `0x42` | JNZ   | `x p`    | if x is not 0, continue at position p          |
  | `0x4F` | STOP  |          | stop the machine                               |

  The manual's rule for everything else: **any command code not in the table
  stops the machine.**

- **Limits.** A program is at most 1024 bytes and a run is at most 4096
  commands. Running past the last byte stops the machine.

## Running a program

```
POST /run   {"program": "<hex bytes>"}

-> {"output": "<hex>",
    "state": {"registers": {"A":..,"B":..,"C":..,"D":..},
              "position": n, "stopped": true|false, "reason": null|"..."},
    "steps": n}
```

Every run starts from a fresh machine, and the same program always gives the
same result. `reason` is `null` after a STOP; otherwise it is a short string
saying why the run ended, for example `unknown command 0x99 at position 4`.

Example: `SET A,0x80 / READ B,A / PLAY B / STOP` is `11008020010030014f`, and
its output is `43`, the first letter on the maker's plate.

```
curl -s localhost:9200/run -H 'Content-Type: application/json' \
     -d '{"program":"11008020010030014f"}'
```

## Goal

The drawer holds a token: 32 ASCII characters of the form `FLAG{...}`.

**Get the box to play it.** You are done when a single `/run` returns the
token as its output. There is nothing to submit anywhere else.

The token is drawn fresh each time the box is started.

## Ground rules

- Only `GET /` and `POST /run` are in play. The puzzle is the machine itself:
  there is nothing to find in the web server, the container or the network.
- No rate limit, and nothing you send can damage the box; runs are independent.
