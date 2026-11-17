#!/usr/bin/env python3
"""
carillon -- a little clockwork music box that runs programs.

A program is a string of bytes. Each byte is a command code, followed by that
command's operand bytes. GET / documents the box in full; POST /run plays a
program on a fresh box and reports what came out.

Two values are drawn once, when the process starts, and never change after:

  TOKEN     32 ASCII bytes kept in the drawer (cells 0xC0..0xDF)
  SPECIAL   one command code that is NOT in the documented table

Every other undocumented code stops the box, exactly as the documentation
says. SPECIAL does not: it releases the drawer catch for the rest of that run,
so drawer cells read back their real contents instead of 0. Nothing served
over HTTP says which code that is, or that such a code exists.

Standard library + Flask. A run is a pure function of the program.
"""
import logging
import secrets
from collections import namedtuple

from flask import Flask, jsonify, request

# --------------------------------------------------------------------------
#  The box
# --------------------------------------------------------------------------
DIALS = ["A", "B", "C", "D"]            # four 8-bit registers
CELLS = 256                             # memory: 256 cells of 8 bits
MAX_PROGRAM = 1024                      # bytes
MAX_STEPS = 4096                        # commands per run

ROLL_START, ROLL_SIZE = 0x00, 0x80      # scratch, read/write
PLATE_START, PLATE_SIZE = 0x80, 0x20    # maker's plate, read-only
DRAWER_START, DRAWER_SIZE = 0xC0, 0x20  # the locked compartment

PLATE = b"CARILLON No.8 * WIND WITH CARE *"
assert len(PLATE) == PLATE_SIZE

Command = namedtuple("Command", "code name operands effect")

# operand kinds: "dial" (0..3), "number" (0..255), "position" (0..255)
COMMANDS = [
    Command(0x10, "REST", [], "nothing happens"),
    Command(0x11, "SET", [("x", "dial"), ("n", "number")], "x = n"),
    Command(0x12, "COPY", [("x", "dial"), ("y", "dial")], "x = y"),
    Command(0x13, "ADD", [("x", "dial"), ("y", "dial")], "x = (x + y) mod 256"),
    Command(0x14, "SUB", [("x", "dial"), ("y", "dial")], "x = (x - y) mod 256"),
    Command(0x15, "AND", [("x", "dial"), ("y", "dial")], "x = x AND y, bit by bit"),
    Command(0x16, "XOR", [("x", "dial"), ("y", "dial")], "x = x XOR y, bit by bit"),
    Command(0x17, "INC", [("x", "dial")], "x = (x + 1) mod 256"),
    Command(0x18, "DEC", [("x", "dial")], "x = (x - 1) mod 256"),
    Command(0x20, "READ", [("x", "dial"), ("y", "dial")],
            "x = the memory cell whose address is the value on dial y"),
    Command(0x21, "WRITE", [("x", "dial"), ("y", "dial")],
            "the memory cell whose address is the value on dial x = y; only the "
            "roll takes writes, anywhere else nothing happens"),
    Command(0x30, "PLAY", [("x", "dial")],
            "append the value on dial x to the output"),
    Command(0x40, "JUMP", [("p", "position")], "continue at program position p"),
    Command(0x41, "JZ", [("x", "dial"), ("p", "position")],
            "if x is 0, continue at program position p"),
    Command(0x42, "JNZ", [("x", "dial"), ("p", "position")],
            "if x is not 0, continue at program position p"),
    Command(0x4F, "STOP", [], "stop the machine"),
]
BY_CODE = {c.code: c for c in COMMANDS}
assert len(BY_CODE) == len(COMMANDS)

# --------------------------------------------------------------------------
#  Drawn once per startup
# --------------------------------------------------------------------------
UNLISTED = [code for code in range(256) if code not in BY_CODE]
SPECIAL = secrets.choice(UNLISTED)
TOKEN = ("FLAG{" + secrets.token_hex(13) + "}").encode("ascii")
assert len(TOKEN) == DRAWER_SIZE


class Box:
    """One fresh machine: zeroed dials, blank roll, drawer catch engaged."""

    def __init__(self):
        self.dials = [0] * len(DIALS)
        self.roll = bytearray(ROLL_SIZE)
        self.catch_released = False
        self.output = bytearray()
        self.position = 0
        self.steps = 0
        self.stopped = False
        self.reason = None

    # -- memory -------------------------------------------------------------
    def cell(self, addr):
        if ROLL_START <= addr < ROLL_START + ROLL_SIZE:
            return self.roll[addr - ROLL_START]
        if PLATE_START <= addr < PLATE_START + PLATE_SIZE:
            return PLATE[addr - PLATE_START]
        if DRAWER_START <= addr < DRAWER_START + DRAWER_SIZE:
            return TOKEN[addr - DRAWER_START] if self.catch_released else 0
        return 0

    def store(self, addr, value):
        if ROLL_START <= addr < ROLL_START + ROLL_SIZE:
            self.roll[addr - ROLL_START] = value

    # -- execution ----------------------------------------------------------
    def halt(self, reason=None):
        self.stopped = True
        self.reason = reason

    def step(self, program):
        pos = self.position
        if pos >= len(program):
            return self.halt("end of program")

        code = program[pos]
        cmd = BY_CODE.get(code)
        if cmd is None:
            if code == SPECIAL:
                self.catch_released = True
                self.position = pos + 1
                self.steps += 1
                return None
            return self.halt("unknown command 0x%02x at position %d" % (code, pos))

        ops = program[pos + 1: pos + 1 + len(cmd.operands)]
        if len(ops) < len(cmd.operands):
            return self.halt("%s at position %d is missing operands" % (cmd.name, pos))
        for (_, kind), value in zip(cmd.operands, ops):
            if kind == "dial" and value >= len(DIALS):
                return self.halt("%s at position %d names dial %d, which does not exist"
                                 % (cmd.name, pos, value))

        self.steps += 1
        nxt = pos + 1 + len(cmd.operands)
        d = self.dials
        name = cmd.name
        if name == "REST":
            pass
        elif name == "SET":
            d[ops[0]] = ops[1]
        elif name == "COPY":
            d[ops[0]] = d[ops[1]]
        elif name == "ADD":
            d[ops[0]] = (d[ops[0]] + d[ops[1]]) & 0xFF
        elif name == "SUB":
            d[ops[0]] = (d[ops[0]] - d[ops[1]]) & 0xFF
        elif name == "AND":
            d[ops[0]] = d[ops[0]] & d[ops[1]]
        elif name == "XOR":
            d[ops[0]] = d[ops[0]] ^ d[ops[1]]
        elif name == "INC":
            d[ops[0]] = (d[ops[0]] + 1) & 0xFF
        elif name == "DEC":
            d[ops[0]] = (d[ops[0]] - 1) & 0xFF
        elif name == "READ":
            d[ops[0]] = self.cell(d[ops[1]])
        elif name == "WRITE":
            self.store(d[ops[0]], d[ops[1]])
        elif name == "PLAY":
            self.output.append(d[ops[0]])
        elif name == "JUMP":
            nxt = ops[0]
        elif name == "JZ":
            if d[ops[0]] == 0:
                nxt = ops[1]
        elif name == "JNZ":
            if d[ops[0]] != 0:
                nxt = ops[1]
        elif name == "STOP":
            return self.halt(None)          # position stays on the STOP
        self.position = nxt
        return None

    def play(self, program):
        while not self.stopped:
            if self.steps >= MAX_STEPS:
                self.reason = "step limit reached"
                break
            self.step(program)
        return {
            "output": self.output.hex(),
            "state": {
                "registers": dict(zip(DIALS, self.dials)),
                "position": self.position,
                "stopped": self.stopped,
                "reason": self.reason,
            },
            "steps": self.steps,
        }


# --------------------------------------------------------------------------
#  HTTP
# --------------------------------------------------------------------------
app = Flask(__name__)
app.json.sort_keys = False


def describe():
    return {
        "machine": "Carillon No.8, a clockwork music box that runs programs",
        "word_bits": 8,
        "registers": {
            "names": DIALS,
            "ids": {name: i for i, name in enumerate(DIALS)},
            "note": "four dials, each holding 0..255; a dial operand is the "
                    "dial's id byte; all four are 0 at the start of every run",
        },
        "program": {
            "format": "a string of bytes: a command code, then that command's "
                      "operand bytes, then the next command code, and so on",
            "position": "index of the next command byte, starting at 0; a "
                        "position operand is one byte, so jumps land in the "
                        "first 256 positions",
            "end": "running past the last byte stops the machine "
                   "(reason \"end of program\")",
            "max_bytes": MAX_PROGRAM,
            "max_steps": MAX_STEPS,
        },
        "commands": [
            {
                "code": c.code,
                "hex": "0x%02x" % c.code,
                "name": c.name,
                "operands": [{"name": n, "kind": k} for n, k in c.operands],
                "length": 1 + len(c.operands),
                "effect": c.effect,
            }
            for c in COMMANDS
        ],
        "unlisted_codes": "any command code not in the table stops the machine",
        "memory": {
            "cells": CELLS,
            "cell_bits": 8,
            "regions": [
                {"name": "roll", "start": ROLL_START, "size": ROLL_SIZE,
                 "access": "read/write",
                 "note": "scratch paper roll; all 0 at the start of every run"},
                {"name": "plate", "start": PLATE_START, "size": PLATE_SIZE,
                 "access": "read-only",
                 "note": "the maker's plate, ASCII"},
                {"name": "blank", "start": PLATE_START + PLATE_SIZE,
                 "size": DRAWER_START - PLATE_START - PLATE_SIZE,
                 "access": "read-only", "note": "always 0"},
                {"name": "drawer", "start": DRAWER_START, "size": DRAWER_SIZE,
                 "access": "locked",
                 "note": "the locked compartment; a read of any of these "
                         "cells gives 0 and a write does nothing"},
                {"name": "blank", "start": DRAWER_START + DRAWER_SIZE,
                 "size": CELLS - DRAWER_START - DRAWER_SIZE,
                 "access": "read-only", "note": "always 0"},
            ],
        },
        "endpoints": {
            "GET /": "this document",
            "POST /run": {
                "body": {"program": "<hex bytes>"},
                "does": "runs the program on a fresh machine and reports the "
                        "result; the same program always gives the same result",
                "returns": {
                    "output": "<hex of every byte PLAYed, in order>",
                    "state": {
                        "registers": "the four dials when the run ended",
                        "position": "where the run ended",
                        "stopped": "true once the machine has stopped; false "
                                   "only if the step limit cut the run short",
                        "reason": "null after STOP, otherwise a short string "
                                  "such as \"unknown command 0x99 at position 4\"",
                    },
                    "steps": "number of commands carried out",
                },
                "example": {
                    "program": "11008020010030014f",
                    "meaning": "SET A,0x80 / READ B,A / PLAY B / STOP",
                    "output": "43",
                },
            },
        },
    }


@app.get("/")
def index():
    return jsonify(describe())


@app.post("/run")
def run():
    body = request.get_json(force=True, silent=True)
    if not isinstance(body, dict) or not isinstance(body.get("program"), str):
        return jsonify({"error": "send JSON like {\"program\": \"<hex bytes>\"}"}), 400
    try:
        program = bytes.fromhex(body["program"])
    except ValueError:
        return jsonify({"error": "program must be hex: two hex digits per byte"}), 400
    if len(program) > MAX_PROGRAM:
        return jsonify({"error": "program is longer than %d bytes" % MAX_PROGRAM}), 400
    return jsonify(Box().play(program))


@app.errorhandler(404)
def not_found(_):
    return jsonify({"error": "no such endpoint; see GET /"}), 404


@app.errorhandler(405)
def bad_method(_):
    return jsonify({"error": "wrong method; see GET /"}), 405


if __name__ == "__main__":
    # Keep secrets out of the logs: nothing drawn at startup is printed.
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    print("[carillon] music box wound; listening on :80", flush=True)
    app.run(host="0.0.0.0", port=80, threaded=True)
