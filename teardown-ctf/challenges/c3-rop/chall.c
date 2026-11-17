// C3 — The Return.  Stack overflow with NX enabled and NO win function.
// Build a ROP chain: pop a pointer to the "/bin/sh" string into rdi and return
// into system@plt. (All addresses are in the no-PIE binary — a classic ret2plt,
// no libc leak required.)
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

char shellcmd[] = "/bin/sh";

// a leftover `pop rdi ; ret` gadget (modern glibc dropped __libc_csu_init, which
// used to provide one). The ROP relies on this.
void __gadget() { __asm__ volatile(".byte 0x5f\n .byte 0xc3\n"); }

// references system() so it is linked into the PLT — but never actually runs.
void __keep() { if (getpid() == -1) system(shellcmd); }

int main() {
    setvbuf(stdout, NULL, _IONBF, 0);
    char buf[64];
    puts("== Vault ==");
    puts("passphrase?");
    read(0, buf, 200);           // overflow, no win()
    puts("access denied");
    return 0;
}
