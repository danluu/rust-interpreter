// Process accounting for one child launched here; never attach or signal.
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <libproc.h>
#include <signal.h>
#include <spawn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

extern char **environ;

static FILE *new_file(const char *path) {
    int fd = open(path, O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC, 0600);
    if (fd < 0) { perror(path); exit(2); }
    FILE *f = fdopen(fd, "w");
    if (!f) { perror("fdopen"); close(fd); exit(2); }
    return f;
}

int main(int argc, char **argv) {
    // The qualification harness uses only these bounded calibration cases.
    if (argc == 3 && strcmp(argv[1], "--spin") == 0) {
        unsigned long count = strtoul(argv[2], NULL, 10);
        if (count > 2000000) return 2;
        volatile uint64_t value = 1;
        for (unsigned long i = 0; i < count; ++i) value = value * 3 + i;
        printf("%" PRIu64 "\n", value);
        return 0;
    }
    if (argc == 2 && strcmp(argv[1], "--exit-seven") == 0) return 7;
    if (argc < 7 || strcmp(argv[5], "--") != 0 || argv[6][0] != '/') {
        fputs("usage: launch counts.json identity.json stdout stderr -- /absolute/program [args]\n", stderr);
        return 2;
    }
    FILE *counts = new_file(argv[1]), *identity = new_file(argv[2]);
    posix_spawn_file_actions_t actions;
    int err = posix_spawn_file_actions_init(&actions);
    if (err) { errno = err; perror("spawn actions"); return 2; }
    err = posix_spawn_file_actions_addopen(&actions, STDOUT_FILENO, argv[3],
        O_WRONLY | O_CREAT | O_EXCL, 0600);
    if (!err) err = posix_spawn_file_actions_addopen(&actions, STDERR_FILENO, argv[4],
        O_WRONLY | O_CREAT | O_EXCL, 0600);
    pid_t child = -1;
    if (!err) err = posix_spawn(&child, argv[6], &actions, NULL, &argv[6], environ);
    posix_spawn_file_actions_destroy(&actions);
    if (err) { errno = err; perror("posix_spawn"); return 2; }
    struct timespec started;
    clock_gettime(CLOCK_REALTIME, &started);
    fprintf(identity, "{\"pid\":%d,\"parent_pid\":%d,\"observed_after_spawn_seconds\":%lld.%09ld}\n",
        child, getpid(), (long long)started.tv_sec, started.tv_nsec);
    fclose(identity);

    // WNOWAIT keeps this exact exited child available until accounting is read.
    // It does not pause execution: the child has already exited on its own.
    siginfo_t info = {0};
    int waited;
    do { waited = waitid(P_PID, child, &info, WEXITED | WNOWAIT); }
    while (waited < 0 && errno == EINTR);
    int wait_error = waited < 0 ? errno : 0;
    struct rusage_info_v4 a = {0}, b = {0};
    int query_error = 0, second_error = 0;
    if (!wait_error && info.si_pid == child) {
        if (proc_pid_rusage(child, RUSAGE_INFO_V4, (rusage_info_t *)&a)) query_error = errno;
        if (proc_pid_rusage(child, RUSAGE_INFO_V4, (rusage_info_t *)&b)) second_error = errno;
    } else query_error = ECHILD;
    int status = 0;
    pid_t reaped;
    do { reaped = waitpid(child, &status, 0); } while (reaped < 0 && errno == EINTR);
    int stable = a.ri_instructions == b.ri_instructions && a.ri_cycles == b.ri_cycles
        && a.ri_proc_start_abstime == b.ri_proc_start_abstime
        && a.ri_proc_exit_abstime == b.ri_proc_exit_abstime;
    fprintf(counts,
        "{\"pid\":%d,\"parent_pid\":%d,\"wait_error\":%d,\"query_error\":%d,"
        "\"second_query_error\":%d,\"waitid_pid\":%d,\"waitid_code\":%d,\"waitid_status\":%d,"
        "\"reaped_pid\":%d,\"exit_code\":%d,\"signal\":%d,\"stable_after_exit\":%s,"
        "\"instructions\":%" PRIu64 ",\"cycles\":%" PRIu64 ","
        "\"user_time\":%" PRIu64 ",\"system_time\":%" PRIu64 ","
        "\"start_abstime\":%" PRIu64 ",\"exit_abstime\":%" PRIu64 "}\n",
        child, getpid(), wait_error, query_error, second_error, info.si_pid, info.si_code, info.si_status,
        reaped, reaped == child && WIFEXITED(status) ? WEXITSTATUS(status) : -1,
        reaped == child && WIFSIGNALED(status) ? WTERMSIG(status) : 0, stable ? "true" : "false",
        a.ri_instructions, a.ri_cycles, a.ri_user_time, a.ri_system_time,
        a.ri_proc_start_abstime, a.ri_proc_exit_abstime);
    fclose(counts);
    return wait_error || query_error || second_error || reaped != child || !stable ? 2 : 0;
}
