/* Diagnostic for explicitly launched owned processes, not a production RNG. */
#include <CommonCrypto/CommonRandom.h>
#include <fcntl.h>
#include <inttypes.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static FILE *tape;
static int recording, entered;
static uint64_t calls, bytes;
static const unsigned char magic[8] = {'R','I','R','N','G','0','0','1'};

static _Noreturn void fail(const char *message) {
    fprintf(stderr, "rust-interp-entropy: %s\n", message);
    _Exit(86);
}

static void transfer(void *data, size_t size) {
    size_t done = recording ? fwrite(data, 1, size, tape) : fread(data, 1, size, tape);
    if (done != size || ferror(tape)) fail("incomplete entropy tape");
}

__attribute__((constructor)) static void initialize(void) {
    const char *mode = getenv("RUST_INTERP_ENTROPY_MODE");
    const char *path = getenv("RUST_INTERP_ENTROPY_TAPE");
    if (!mode || !path || !*path) fail("explicit mode and tape are required");
    if (!strcmp(mode, "record")) recording = 1;
    else if (strcmp(mode, "replay")) fail("unknown entropy mode");
    int flags = recording ? O_WRONLY | O_CREAT | O_EXCL : O_RDONLY;
    int fd = open(path, flags | O_CLOEXEC | O_NOFOLLOW, 0600);
    if (fd < 0) fail("cannot open exclusive regular entropy tape");
    struct stat info;
    if (fstat(fd, &info) || !S_ISREG(info.st_mode) || info.st_uid != geteuid()) fail("invalid entropy tape owner/type");
    if (info.st_size > 17 * 1024 * 1024) fail("entropy tape too large");
    tape = fdopen(fd, recording ? "wb" : "rb");
    if (!tape) fail("cannot open entropy stream");
    unsigned char header[8];
    memcpy(header, magic, sizeof(header));
    transfer(header, sizeof(header));
    if (memcmp(header, magic, sizeof(header))) fail("invalid entropy tape header");
}

static CCRNGStatus captured_random(void *destination, size_t count) {
    if (!pthread_main_np() || entered) fail("entropy diagnostic requires the main thread without recursion");
    if (!tape || count > 1024 * 1024 || calls >= 4096 || bytes + count > 16 * 1024 * 1024)
        fail("entropy request exceeds diagnostic bound");
    entered = 1;
    unsigned char length[8];
    uint64_t requested = count;
    for (unsigned i = 0; i < 8; i++) length[i] = (unsigned char)(requested >> (8 * i));
    if (recording) {
        CCRNGStatus status = CCRandomGenerateBytes(destination, count);
        if (status != kCCSuccess) fail("real entropy request failed");
        transfer(length, sizeof(length));
        transfer(destination, count);
    } else {
        transfer(length, sizeof(length));
        uint64_t recorded = 0;
        for (unsigned i = 0; i < 8; i++) recorded |= (uint64_t)length[i] << (8 * i);
        if (recorded != requested) fail("entropy request length differs");
        transfer(destination, count);
    }
    calls++;
    bytes += count;
    entered = 0;
    return kCCSuccess;
}

/* The replacement's direct call resolves to the original implementation. */
__attribute__((used, section("__DATA,__interpose,interposing")))
static const struct { const void *replacement; const void *original; } interpose = {
    (const void *)&captured_random, (const void *)&CCRandomGenerateBytes
};

__attribute__((destructor)) static void finish(void) {
    if (!tape) fail("entropy stream was not initialized");
    if (!recording && (fgetc(tape) != EOF || ferror(tape))) fail("unconsumed entropy tape");
    if (fclose(tape)) fail("cannot finish entropy tape");
    fprintf(stderr, "rust-interp-entropy entropy_calls=%" PRIu64 " entropy_bytes=%" PRIu64 "\n", calls, bytes);
}
