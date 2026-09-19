# Bounded register workspace for ordinary JIT emission

The candidate replaces temporary tree maps and sets during ordinary region
generation with reusable dense storage, where a function's register count and
storage budget permit it. It passed correctness qualification but failed its
changed-source end-to-end gate. It is parked and is not adopted.

All32 parser commands completed with exact native outcomes and artifact/catalog
agreement, unchanged assertions and restored source. Five valid edited pairs
give candidate/adopted wall ratio1.058596 with A/A envelope0.060960 and margin
1.119556. CPU ratio1.046235 and margin1.100248 also fail. The wall result is
5.86% higher amid6.10% control variation, not a precise estimate of a regression.
Candidate/native wall ratio is1.352372. Larger comparisons are cancelled, with
no unchanged retry. [Closed primary](../results/emitter-register-workspace-parser-screen-incremental-01/summary.json).

The preparation census found ordinary region generation taking about74/56ms
per pgrust worker and92/66ms per fre worker. These are nested diagnostic elapsed
intervals, with overlapping workers and observer overhead, not CPU savings.
The change targets repeated host allocation and register lookup in this stage.
It does not defer type or borrow checking, change guest budgets, or introduce
a different JIT backend.

Each function reuses three region-local tables: facts, definitions and live-in
membership. Dense storage is limited to65,536 registers and4MiB of combined
vector payload. Clearing resets touched entries before reuse. Flush traversal
preserves ascending register order. Larger functions, optional allocation
failures and other emitter paths retain sparse storage. The bound does not
include allocator overhead or promise a process RSS limit.

The model and integration checks cover update/removal/reinsertion, reset,
fallback, storage bounds, region boundaries, joins, loops, profiling options and
code capacities. Both saved current adopted fre machine-code arenas reconstruct
exactly, including scalar targets, assertions and operation maps. The full
build passes615 Rust tests per profile (13 ignored),434 Python tests (22 skipped),
and121 strict compiler/cache commands including unreachable type/borrow errors
and actual partial-artifact rejection. Earlier test/compilation bookkeeping
failures and lock admission failures remain recorded with their corrections.

Candidate tool:
`78176777e223ad180f5c47c2a2c28f040a806e63979965c46e0f2bee0614b879`.
Candidate VM:
`5ec0cc0ef6b3f26335f383ea160e26b63290407f3ab7fde9392fe25da84b0297`.
It uses the exact adopted exporter and wrapper. No preparation observer is
included. The selected-function/test-body execution scope remains unchanged.

The completed primary compares ordinary native, adopted, duplicate adopted
and candidate commands across five real parser edits plus original, wrong and
restored controls. All114 original pgrust parser tests and assertions remain.
Only the five valid edits enter timing. Wall ratio plus A/A variation must be
below1; CPU ratio must be at most1 and its variation margin at most1.05. A failed
gate with greater than8% A/A variation is labeled unmeasurable. Any nonpass
cancels larger histories; there is no unchanged retry. A pass still requires
the larger and regression comparisons before adoption.

Qualification receipts are in
[build](../results/emitter-register-workspace-build-01/summary.json),
[strict checks](../results/emitter-register-workspace-qualification-01/summary.json),
[reconstruction](../results/emitter-register-workspace-reconstruction-01/summary.json)
and [protocol](../results/emitter-register-workspace-parser-protocol-01/summary.json).
The [prospective protocol](../benchmarks/experiments/emitter-register-workspace-screen/PLAN.md)
reserved24GiB initially and checked an8GiB floor before every child command.

Next audit the15 already-recorded valid edited custom receipts for constructor
and compilation intervals. No new guest runs are needed. The descriptive stage
audit cannot change the failed gate or establish recoverable command savings.
