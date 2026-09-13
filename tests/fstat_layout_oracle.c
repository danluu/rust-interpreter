/* Independent Darwin SDK oracle. No Rust stat declaration supplies this layout. */
#define _DARWIN_C_SOURCE 1
#include <sys/stat.h>
#include <sys/types.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>

#define FIELDS(X) \
 X(st_dev,0,4) X(st_mode,4,2) X(st_nlink,6,2) X(st_ino,8,8) \
 X(st_uid,16,4) X(st_gid,20,4) X(st_rdev,24,4) \
 X(st_atimespec.tv_sec,32,8) X(st_atimespec.tv_nsec,40,8) \
 X(st_mtimespec.tv_sec,48,8) X(st_mtimespec.tv_nsec,56,8) \
 X(st_ctimespec.tv_sec,64,8) X(st_ctimespec.tv_nsec,72,8) \
 X(st_birthtimespec.tv_sec,80,8) X(st_birthtimespec.tv_nsec,88,8) \
 X(st_size,96,8) X(st_blocks,104,8) X(st_blksize,112,4) \
 X(st_flags,116,4) X(st_gen,120,4) X(st_lspare,124,4) \
 X(st_qspare[0],128,8) X(st_qspare[1],136,8)
_Static_assert(sizeof(struct stat) == 144, "Darwin stat size");
_Static_assert(_Alignof(struct stat) == 8, "Darwin stat alignment");
#define CHECK(member,offset,width) \
 _Static_assert(offsetof(struct stat, member) == offset, "stat offset " #member); \
 _Static_assert(sizeof(((struct stat *)0)->member) == width, "stat width " #member);
FIELDS(CHECK)
#undef CHECK

int main(int argc, char **argv) {
    if (argc == 2 && strcmp(argv[1], "--layout") == 0) {
        printf("{\"size\":%zu,\"align\":%zu,\"offsets\":[", sizeof(struct stat), _Alignof(struct stat));
        int first = 1;
#define OFFSET(member,offset,width) printf("%s%zu", first ? "" : ",", offsetof(struct stat, member)); first = 0;
        FIELDS(OFFSET)
#undef OFFSET
        printf("],\"widths\":["); first = 1;
#define WIDTH(member,offset,width) printf("%s%zu", first ? "" : ",", sizeof(((struct stat *)0)->member)); first = 0;
        FIELDS(WIDTH)
#undef WIDTH
        puts("]}"); return 0;
    }
    if (argc != 3 || strcmp(argv[1], "--stat") != 0) return 2;
    int fd = open(argv[2], O_RDONLY);
    if (fd < 0) return 3;
    /* The API receives a declared stat object; char access retains its complete
       initialized representation, including padding. */
    union { struct stat value; unsigned char bytes[sizeof(struct stat)]; } storage;
    memset(storage.bytes, 0xa5, sizeof(storage.bytes));
    unsigned char *bytes = storage.bytes;
    errno = 71;
    int result = fstat(fd, &storage.value);
    int error = errno;
    printf("{\"returncode\":%d,\"errno\":%d,\"bytes\":[", result, error);
    for (size_t i = 0; i < sizeof(storage.bytes); ++i) printf("%s%u", i ? "," : "", bytes[i]);
    printf("],\"fields\":[");
    /* Read each SDK-declared member separately; no struct copy/padding reads. */
    int first = 1;
#define VALUE(member,offset,width) do { __typeof__(((struct stat *)0)->member) value; \
 memcpy(&value, bytes + offsetof(struct stat, member), sizeof(value)); \
 printf("%s%llu", first ? "" : ",", (unsigned long long)(uint64_t)value); first = 0; } while (0);
    FIELDS(VALUE)
#undef VALUE
    puts("]}");
    int closed = close(fd);
    return result == 0 && closed == 0 ? 0 : 4;
}
