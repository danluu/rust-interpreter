# Fixed frame clearing passes the runtime screen

Six alternating pairs on the unchanged es8i artifact improve median paired
JIT wall time **11.41%** and CPU time **11.42%**. Median baseline/candidate
runtime is 2.999/2.659 seconds. All 14 commands, including the excluded warm
pair, return the original result with exactly 19,404,293,042 instructions and
the same peak guest memory. This passes the predeclared 10.3% runtime threshold.
It is a runtime screen, not an end-to-end speedup claim.

Both VMs were built from the same absolute source directory and target, with
the same pinned compiler, release settings, one level of debug information,
no incremental compilation and two build jobs. The baseline includes the
previously merged general interpreter improvements. The candidate changes
only small, statically sized guest-frame clears; bytecode, register clearing,
argument copying, assertions and budget charging are unchanged.

The candidate passes all 258 bytecode tests in debug and release, with one
preexisting ignored test. New tests execute 16,448 exact dirty buffer ranges,
check alignment calculations, and exercise 39 dirty guest-frame layouts under
both register modes and instruction, memory and frame limits. Padding and
spare host bytes are checked explicitly.

The first build launch and first screen launch encountered the shared lock
before starting any build or VM command. Their terminal failure receipts remain.
The subsequent launches completed; no timing failure was retried. The next gate
is five real es8 production edits with matched baseline/candidate tools and
native/check controls, requiring at least 8% paired custom command improvement.
