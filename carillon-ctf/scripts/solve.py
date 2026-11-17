#!/usr/bin/env python3
"""
carillon -- reference solver.

  1. GET /  -> the command table (SET, READ, PLAY, STOP and their operand
     layouts), the locked compartment's address and size, and the set of
     listed codes. The unlisted set is every other byte value.
  2. Try every unlisted code. For each one, run
         <code> / SET B,<first drawer cell> / READ A,B / PLAY A / STOP
     An ordinary unlisted code stops the machine on the spot, so nothing is
     played. The special one lets the run carry on, and the drawer cell it
     then reads is real data instead of 0.
  3. Run  <special code> + (SET B,addr / READ A,B / PLAY A) for every drawer
     cell + STOP. The output is the token.
  4. Print  TOKEN: <token>

Nothing here knows the special code in advance: it is found by the sweep in
step 2, from the machine's behaviour alone.

Standard library only. Override the target with CARILLON_URL
(e.g. http://localhost:9200 from the host).
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = os.environ.get("CARILLON_URL", "http://app").rstrip("/")


def say(msg):
    print(msg, flush=True)


def call(path, body=None, tries=6, pause=0.2):
    """One JSON request. Every endpoint is pure, so retrying is safe."""
    data = None if body is None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json"} if data else {}
    last = None
    for attempt in range(1, tries + 1):
        try:
            req = urllib.request.Request(BASE + path, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise SystemExit("HTTP %d from %s: %s" % (exc.code, path, detail))
        except (urllib.error.URLError, OSError, ValueError) as exc:
            last = exc
            time.sleep(pause * attempt)
    raise SystemExit("no answer from %s%s: %s" % (BASE, path, last))


def wait_for_service(seconds=60):
    """The box may still be starting right after `make up` / `make reset`."""
    deadline = time.time() + seconds
    while True:
        try:
            with urllib.request.urlopen(BASE + "/", timeout=5) as resp:
                return json.loads(resp.read().decode())
        except (urllib.error.URLError, OSError, ValueError) as exc:
            if time.time() > deadline:
                raise SystemExit("service at %s never came up: %s" % (BASE, exc))
            time.sleep(0.5)


class Assembler:
    """Turns command names + operands into bytes, using only the table."""

    def __init__(self, doc):
        self.commands = {c["name"]: c for c in doc["commands"]}
        self.dial = doc["registers"]["ids"]

    def __call__(self, name, *operands):
        cmd = self.commands[name]
        kinds = [op["kind"] for op in cmd["operands"]]
        if len(kinds) != len(operands):
            raise SystemExit("%s takes %d operands" % (name, len(kinds)))
        out = [cmd["code"]]
        for kind, value in zip(kinds, operands):
            out.append(self.dial[value] if kind == "dial" else value)
        return bytes(out)


def run(program):
    return call("/run", {"program": program.hex()})


def main():
    # ---- 1. read the documentation --------------------------------------
    doc = wait_for_service()
    asm = Assembler(doc)
    for needed, layout in (("SET", ["dial", "number"]), ("READ", ["dial", "dial"]),
                           ("PLAY", ["dial"]), ("STOP", [])):
        have = [op["kind"] for op in asm.commands[needed]["operands"]]
        if have != layout:
            raise SystemExit("unexpected operand layout for %s: %s" % (needed, have))

    listed = {c["code"] for c in doc["commands"]}
    unlisted = [code for code in range(256) if code not in listed]
    locked = [r for r in doc["memory"]["regions"] if r["access"] == "locked"]
    if len(locked) != 1:
        raise SystemExit("expected one locked region, found %d" % len(locked))
    start, size = locked[0]["start"], locked[0]["size"]

    say("[solve] machine: %s" % doc["machine"])
    say("[solve] %d listed commands, %d unlisted codes" % (len(listed), len(unlisted)))
    say("[solve] locked compartment '%s': cells 0x%02x..0x%02x (%d cells)"
        % (locked[0]["name"], start, start + size - 1, size))

    # One drawer cell, read and played.
    probe = asm("SET", "B", start) + asm("READ", "A", "B") + asm("PLAY", "A") + asm("STOP")

    # Control: with listed commands only, the drawer reads as 0.
    control = run(probe)
    say("[solve] control (listed commands only): output %s, reason %r"
        % (control["output"], control["state"]["reason"]))
    if control["output"] != "00":
        raise SystemExit("control run did not read 0 from the locked compartment")

    # ---- 2. try the unlisted codes --------------------------------------
    halted, different = [], []
    for code in unlisted:
        res = run(bytes([code]) + probe)
        reason = res["state"]["reason"] or ""
        if reason.startswith("unknown command") and res["output"] == "":
            halted.append(code)
        else:
            different.append((code, res))

    say("[solve] tried %d unlisted codes: %d stopped the machine, %d did not"
        % (len(unlisted), len(halted), len(different)))
    for code, res in different:
        say("[solve]   0x%02x -> output %s, steps %d, reason %r"
            % (code, res["output"], res["steps"], res["state"]["reason"]))

    opens = [code for code, res in different
             if res["output"] not in ("", "00") and res["state"]["stopped"]]
    if len(opens) != 1:
        raise SystemExit("expected exactly one code that opens the compartment, "
                         "found %d" % len(opens))
    special = opens[0]
    say("[solve] special command: 0x%02x (the compartment read after it returned "
        "real data)" % special)

    # ---- 3. open the compartment and read every cell --------------------
    program = bytes([special])
    for addr in range(start, start + size):
        program += asm("SET", "B", addr) + asm("READ", "A", "B") + asm("PLAY", "A")
    program += asm("STOP")

    res = run(program)
    raw = bytes.fromhex(res["output"])
    say("[solve] full read: %d-byte program, %d steps, %d bytes out"
        % (len(program), res["steps"], len(raw)))
    if len(raw) != size or res["state"]["reason"] is not None:
        raise SystemExit("full read went wrong: %s" % json.dumps(res))

    token = raw.rstrip(b"\x00").decode("ascii")
    if not token or not token.isprintable():
        raise SystemExit("compartment contents are not a printable token: %r" % raw)

    # ---- 4. report -------------------------------------------------------
    say("TOKEN: %s" % token)
    return 0


if __name__ == "__main__":
    sys.exit(main())
