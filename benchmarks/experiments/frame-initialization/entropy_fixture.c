#include <CommonCrypto/CommonRandom.h>
#include <inttypes.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static void *other_thread(void *unused) {
    (void)unused;
    unsigned char bytes[16];
    CCRandomGenerateBytes(bytes, sizeof(bytes));
    return NULL;
}

int main(int argc, char **argv) {
    const char *mode = argc == 2 ? argv[1] : "normal";
    if (!strcmp(mode, "none")) return 0;
    if (!strcmp(mode, "thread")) {
        pthread_t thread;
        if (pthread_create(&thread, NULL, other_thread, NULL)) return 2;
        return pthread_join(thread, NULL) != 0;
    }
    size_t lengths[] = {1, 16, 33, 7};
    size_t requests = !strcmp(mode, "short") ? 2 : !strcmp(mode, "extra") ? 4 : 3;
    if (!strcmp(mode, "different")) lengths[0] = 2;
    uint64_t checksum = 14695981039346656037ULL;
    for (size_t i = 0; i < requests; i++) {
        unsigned char bytes[33];
        if (CCRandomGenerateBytes(bytes, lengths[i]) != kCCSuccess) return 3;
        for (size_t j = 0; j < lengths[i]; j++) checksum = (checksum ^ bytes[j]) * 1099511628211ULL;
    }
    printf("%" PRIu64 "\n", checksum);
    return 0;
}
