#include <stdio.h>
#include <stdlib.h>

extern int setupAndStartPlayer();

int main(void) {
        printf("Setting up player\n");
        setupAndStartPlayer();
        return 0;
}