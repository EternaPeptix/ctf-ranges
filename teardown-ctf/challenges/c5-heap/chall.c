// C5 — The Freelist.  A note manager with a use-after-free: delete() frees a
// chunk but does not null the pointer, and edit()/view() will touch a freed
// chunk. Modern-glibc (2.32+) tcache poison: leak the heap via a UAF read of a
// freed chunk's (safe-linking-mangled) fd, then overwrite a freed chunk's fd so
// malloc hands back a chunk AT &hidden; write &shell there and "run" it.
// -no-pie, so &hidden and shell() are fixed addresses; hidden is 16-aligned so
// it passes glibc's tcache alignment check.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

void shell() { system("/bin/cat /flag"); }
void (*hidden)(void) __attribute__((aligned(16))) = NULL;

static char *notes[16];
static int sizes[16];

static int rd_int() {
    char b[16] = {0};
    read(0, b, 15);
    return atoi(b);
}

int main() {
    setvbuf(stdout, NULL, _IONBF, 0);
    while (1) {
        puts("1.new 2.edit 3.view 4.delete 5.run 6.exit");
        int c = rd_int();
        if (c == 1) {
            printf("idx:");  int i = rd_int();
            printf("size:"); int s = rd_int();
            if (i < 0 || i >= 16) continue;
            notes[i] = malloc(s); sizes[i] = s;
        } else if (c == 2) {
            printf("idx:");  int i = rd_int();
            if (i < 0 || i >= 16 || !notes[i]) continue;
            printf("data:");
            read(0, notes[i], sizes[i]);          // UAF: no check the chunk is live
        } else if (c == 3) {
            printf("idx:");  int i = rd_int();
            if (i < 0 || i >= 16 || !notes[i]) continue;
            write(1, notes[i], sizes[i]);
        } else if (c == 4) {
            printf("idx:");  int i = rd_int();
            if (i < 0 || i >= 16) continue;
            free(notes[i]);                       // UAF: pointer not nulled
        } else if (c == 5) {
            if (hidden) hidden();
        } else {
            break;
        }
    }
    return 0;
}
