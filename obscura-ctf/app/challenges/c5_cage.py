"""c5 — cage : "Safe formula sandbox."

Submit a program in a tiny stack bytecode.  A static *verifier* runs first and
rejects anything that uses the privileged READFLAG opcode (0x20); only verified
programs are executed by the VM.

ISA (1-byte opcodes; PUSH and JMP carry a 1-byte immediate):
    0x00 HALT
    0x01 PUSH imm      push imm (0..255)
    0x02 ADD           a,b -> (a+b)&0xff
    0x03 XOR           a,b -> a^b
    0x04 OUT           pop -> append to output
    0x10 JMP imm       pc <- imm   (absolute byte offset)
    0x20 READFLAG      append the flag to output   (BLOCKED by the verifier)

Flaw (original): the verifier decodes instructions by a single LINEAR SCAN from
offset 0 and only checks that JMP targets are in-bounds — it never checks that a
target lands on an instruction *boundary* it scanned.  The VM, however, sets the
program counter to the exact target.  Jump into the middle of a PUSH and its
immediate byte is re-decoded as an opcode.  Hide 0x20 as a PUSH immediate, then
JMP onto it: the verifier only ever saw it as data.
"""
from flask import Flask, request, jsonify

FLAG = "FLAG{cage_verifier_scans_linearly_the_vm_jumps_anywhere_c0ffee}"

HALT, PUSH, ADD, XOR, OUT, JMP, READFLAG = 0x00, 0x01, 0x02, 0x03, 0x04, 0x10, 0x20
_WIDE = {PUSH, JMP}                          # opcodes that consume an immediate
_KNOWN = {HALT, PUSH, ADD, XOR, OUT, JMP, READFLAG}

app = Flask(__name__)


def verify(code):
    """Linear disassembly: reject READFLAG / unknown ops / out-of-range jumps."""
    pc = 0
    while pc < len(code):
        op = code[pc]
        if op == READFLAG:
            return False, "forbidden opcode READFLAG(0x20) at %d" % pc
        if op not in _KNOWN:
            return False, "unknown opcode 0x%02x at %d" % (op, pc)
        if op in _WIDE:
            if pc + 1 >= len(code):
                return False, "truncated immediate at %d" % pc
            if op == JMP and not (0 <= code[pc + 1] < len(code)):
                return False, "jmp target out of range at %d" % pc
            pc += 2
        else:
            pc += 1
    return True, "ok"


def run(code, limit=100000):
    pc, st, out, steps = 0, [], bytearray(), 0
    while pc < len(code) and steps < limit:
        steps += 1
        op = code[pc]
        if op == HALT:
            break
        elif op == PUSH:
            st.append(code[pc + 1]); pc += 2
        elif op == ADD:
            b = st.pop(); a = st.pop(); st.append((a + b) & 0xff); pc += 1
        elif op == XOR:
            b = st.pop(); a = st.pop(); st.append((a ^ b) & 0xff); pc += 1
        elif op == OUT:
            out.append(st.pop() & 0xff); pc += 1
        elif op == JMP:
            pc = code[pc + 1]
        elif op == READFLAG:
            out.extend(FLAG.encode()); break
        else:
            return out, "trap: bad opcode 0x%02x" % op
    return out, "ok"


@app.get("/")
def home():
    return jsonify(
        widget="cage — verified formula sandbox",
        isa={
            "0x00": "HALT", "0x01": "PUSH imm", "0x02": "ADD", "0x03": "XOR",
            "0x04": "OUT", "0x10": "JMP imm (absolute)", "0x20": "READFLAG (blocked)",
        },
        endpoints={"POST /run {program: <hex>}": "verify then execute; returns output"},
        note="The verifier rejects any program that uses READFLAG(0x20).",
    )


@app.post("/run")
def run_ep():
    j = request.get_json(silent=True) or {}
    prog = j.get("program", "")
    try:
        code = bytes.fromhex(prog)
    except ValueError:
        return jsonify(error="program must be hex"), 400
    ok, why = verify(code)
    if not ok:
        return jsonify(verified=False, reason=why), 400
    out, status = run(code)
    try:
        text = out.decode()
    except UnicodeDecodeError:
        text = out.hex()
    return jsonify(verified=True, status=status, output=text)
