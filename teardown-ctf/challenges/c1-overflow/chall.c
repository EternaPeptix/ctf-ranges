// C1 — The Overflow.  Classic stack buffer overflow -> ret2win.
// Compiled -no-pie -fno-stack-protector, so win()'s address is fixed and the
// saved return address is clobberable. (Return via a `ret` gadget to keep the
// stack 16-byte aligned for the libc call inside win.)
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

void win() {
    char flag[96];
    FILE *f = fopen("/flag", "r");
    if (f) {
        size_t n = fread(flag, 1, 95, f);
        flag[n] = 0;
        fputs(flag, stdout);
        fclose(f);
    } else {
        puts("flag missing");
    }
    fflush(stdout);
}

int main() {
    setvbuf(stdout, NULL, _IONBF, 0);
    char buf[64];
    puts("== Register ==");
    puts("name?");
    read(0, buf, 256);          // overflow
    puts("thanks for registering");
    return 0;
}
