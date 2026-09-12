# Reproducible generated control-flow coverage

Retain the new integration tests. All362workspace tests pass in debug and
release (one ignored), including32default generated seeds. A further768distinct
seeds pass in both host profiles: ordinary seeds32–287,256seeds from2^63, and
the highest256u64seeds. This is1,536additional seed/profile cases, each checking
six instruction budgets, persistent-register choices, three code capacities
and profiled/unprofiled JIT execution against the interpreter.

The generator builds bounded two-function programs with diamonds, counted
loops, calls, heap/linear memory, overlapping copies, reused registers and
arithmetic/cast/load/store widths. Returned checksums observe mutable values
and memory. Successful runs match results, instructions, peak memory and every
profiled PC count. Native coverage is required when the code capacity permits
it. A mismatch writes an exact bytecode reproducer, seed, argument and settings
into a new directory. No mismatch occurred in this campaign.

The source is `7bf3593`. Both workspace test profiles finished successfully.
The build controller then stopped at its4GiB admission guard, before starting
the final VM-build command (4,293,574,656bytes available). That failed controller
receipt remains preserved. This is a tests-only change; qualification uses the
completed test logs and their exact executables, without publishing a new VM.
Runtime/compiler sources are unchanged. [Campaign and provenance](summary.json).

These tests improve engine correctness coverage; they neither establish new
Rust frontend coverage nor measure development latency. Next investigate
parallel isolated test workers: native controls use concurrent libtest tests,
while the custom prepared-suite runner currently executes serially. Each
worker must create and retain its own JIT on its own thread, with fresh guest
memory/statics/TLS per test and deterministic report ordering.
