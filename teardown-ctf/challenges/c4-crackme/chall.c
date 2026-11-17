// C4 — The Lock.  A reverse-engineering crackme. The 16-byte serial is
// transformed byte-by-byte and compared to a fixed target; recover the serial
// by inverting the transform:  serial[i] = ((target[i] - 7) & 0xff) ^ (0x41 + i).
// On the right serial it prints /flag. (Flag is NOT in the binary — only the
// target is, so `strings` won't give it away.)
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int check(unsigned char *s) {
    unsigned char t[16];
    for (int i = 0; i < 16; i++)
        t[i] = (unsigned char)(((s[i] ^ (0x41 + i)) + 7) & 0xff);
    unsigned char target[16] = {
        0x2d,0x79,0x23,0x3d,0x7d,0x37,0x7b,0x41,
        0x41,0x80,0x1b,0x28,0x85,0x18,0x46,0x43
    };
    return memcmp(t, target, 16) == 0;
}

static void win() {
    char flag[96];
    FILE *f = fopen("/flag", "r");
    if (f) { size_t n = fread(flag, 1, 95, f); flag[n] = 0; fputs(flag, stdout); fclose(f); }
    fflush(stdout);
}

int main() {
    setvbuf(stdout, NULL, _IONBF, 0);
    unsigned char buf[32] = {0};
    puts("== License Check ==");
    puts("serial (16 chars):");
    read(0, buf, 16);
    if (check(buf)) { puts("valid license!"); win(); }
    else puts("invalid serial");
    return 0;
}
