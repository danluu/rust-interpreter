# Runtime-only qualification and storage admission

The scope is closed at bcbc009d. Tail self-PC coverage is39/797 and52/609 on
ES8,66/1933 and39/1429 on the two current token captures. Ten pattern mutations
and unaligned matches are rejected;1024 native-tail-model canary cases, empty
one-past-end and overwide-store negative controls pass. Clang's independent
AArch64 assembly produces all nine exact proposed words. No guest was run.

The candidate changes only native_calls.rs's zero_range tail and adds one direct
native helper contract test in resumable_tests.rs. The16-byte chunk path is exact.
On the tail, x9 remains a0..15 remainder and x11 advances exactly to x12. CBZ/TBZ
do not set flags; the old exit left comparison flags. Every caller was audited:
scalar success sets its own peak-memory comparison; native-tree calls set their
own peak comparison or perform argument/register handling with independent
guards; resumable padding/clear paths proceed through stores and their own peak
comparison. No caller consumes the helper's final flags. x9/x10/flags are scratch;
the live Call/Return registers remain unchanged. The new native test covers every
length0..512 plus1023/1024/1025/4095/4096/4097 at64 starting alignments, full dirty
prefix/suffix canaries, exact final cursor and12 live registers.

Create only .work/short-clear-tail-runtime-build-01/target, with an owner manifest.
It starts empty. Keep the existing .work/fixed-frame-clear-combined-build-01/target
untouched; its26.63GB floor is unchanged. For this new target require at least
max(14GiB,8GiB+2*its allocated bytes) before each Cargo child. Initially this
reserves6GiB growth above the8GiB floor, despite compiling only one runtime crate
and dependencies. Cap the target at3GiB allocated between commands; exceeding
that stops further work for reassessment. Inspect free space after each command.
No concurrent build, implicit cleanup, broad process control or weaker floor.

Use two Cargo jobs/two test workers, offline locked nightly2026-09-08,
nonincremental compilation, debug0 development/test and release debug1. Record
the cold setup wall and child-tree CPU, command identity and allocation before
and after. Focused qualification runs all six existing zeroing/frame-clear tests
plus the new short-tail contract, separately in debug and release. It exercises
native machine code, not just an encoding model. Freeze sources until terminal
and independent closure. Do not run original-project timings yet.

After focused success, a separate immutable full-workspace/strict frontend and
guest-profile qualification is required. A runtime-only tool composition may
reuse byte-identical already qualified exporter/wrapper binaries because neither
frontend nor artifact generation changes. Only the new VM may change; keep the
default installed tool unchanged. Re-evaluate storage before that larger stage.
