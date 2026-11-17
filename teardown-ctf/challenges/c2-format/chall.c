// C2 — The Mirror.  Format-string vulnerability: printf(user_input).
// Use %n writes to set the global `authed` to the magic value and reach shell().
// -no-pie, so &authed and shell() are at fixed addresses.
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

unsigned int authed = 0;

void shell() {
    system("/bin/cat /flag");
}

int main() {
    setvbuf(stdout, NULL, _IONBF, 0);
    char buf[200];
    puts("== Echo Service ==");
    puts("say something:");
    int n = read(0, buf, 199);
    if (n > 0) buf[n] = 0;
    printf(buf);                 // format-string bug
    putchar('\n');
    if (authed == 0xc0ffee) shell();
    return 0;
}
