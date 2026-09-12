# Call capacity credit qualification

The completed process diagnostic reports 7.132 times the native instructions
and 4.398 times the native cycles for the original exhaustive token test.
Proceed with the conservative credit described in DESIGN.md. This is a new
runtime implementation, not another trial of the previous failed candidate.

The candidate uses x30 between resumable external entry and exit, after saving
the host return address. Each external entry starts with zero credit. A checked
slow Call computes the minimum exact post-call slack in memory bytes, register
bytes and working-budget bytes. A successful conservative cost subtraction
permits the fast capacity path. Keep target readiness and frame depth separate,
retain actual alignment, and never refund credit on Return. Preserve all
argument/copy checks, clearing order, descriptors and logical instruction counts.
No guest memory layout, RBC format, type checking or borrow checking changes.

Add four tests: wide-integer cost/overflow checks; a mixed-call/return arithmetic
invariant; scalar emitted checks over independent capacity boundaries and valid
credit seeds without accessing guest buffers; and repeated real calls with
small/exact memory and instruction limits. Existing dirty-frame, high-register,
TLS, ABI, profile and generated-CFG tests remain enabled. No historical unsafe
VM or memory-corruption reproduction is used.

Run all 422 workspace tests in debug and release, one ignored, with two Cargo
workers and locked offline dependencies. Host qualification floor: 4 GiB.
Reuse the existing qualified debug/release host dependency cache at
`.work/fixed-frame-clear-combined-build-01/target`; this is a host-only build,
not a new large-project target. Use the shared benchmark lock with 45-second
admission and check the free floor before each child.
Freeze source and plan. Publish immutable VM bytes while retaining exporter and
wrapper from qualified integrated tool49746a22. No exporter source changed.

After host qualification, run the seven exact saved selections, nine serial/
prepared-suite checks and 203 strict native/cache checks against the new VM.
Only then freeze the prospective token/folded/pgrust complete-command driver,
using the same integrated exporter in baseline and candidate, an independent
A/A cache, fixed selected-suite anchor, ordinary native, line-tables native and
check. Use all fifteen edit pairs and original/wrong/restored assertions. Keep
the declared composed 8% anchor target, effect beyond observed A/A noise for
the mechanism, CPU/noise bounds and held-out guards. Retain every failed/noisy
observation; no repeat of an unchanged candidate to obtain a pass. Defaults
remain unchanged until the complete qualification and comparison is assessed.
