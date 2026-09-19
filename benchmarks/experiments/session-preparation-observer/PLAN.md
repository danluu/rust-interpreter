# Diagnose remaining preparation and exact compile declines

The reduced-request candidate failed its unchanged primary wall gate. Do not
retime it. Its closed report shows146.9ms summed test-compilation intervals;
earlier closed traces attribute23.9ms per worker to an ordinary emission attempt
that publishes no entry. The exact cause is unknown, including whether it is a
code budget, branch encoding, resume table or other limit.

Add an explicit jit-preparation-observer feature depending on jit-template-session.
It changes no native instructions, limits, keys, admission or fallback decisions.
Record aggregate elapsed scalar preparation, ordinary staging (including history)
and publication intervals. Retain at most64 exact non-staging/limit records per
owner with a truncation count. Each records current numeric function ID, operation
count, remaining word budget, actual EmitError category and exact no-staging site
when available. No runtime guess becomes an early decline.

Reports bind these diagnostic rows to the current artifact. No function names or
unbounded event stream is needed. Report durations include instrumentation and
may overlap across workers; they are not CPU or end-to-end speedup evidence.
Existing per-test/constructor counters retain their original definitions.

Qualify31 controls/profile:4 wire,8 prepared,9 history/observer,10 actual session
controls. The new observer control executes71 real code-budget declines and
checks exact fallback outcomes and the64-record bound.24 owned sessions and46 VM
clients must be reaped. Then replay16 real saved parser suites history off/on,
with verification disabled only for phase attribution (existing independent
correctness replay already verifies all hits). Original outcomes and exact wrong
assertion text, current artifacts, report bounds and kernel CPU must match.
Keep diagnostic binaries separate from every candidate or adopted timing binary.

All stages hold .work/benchmark.lock with45-second admission and two workers.
Build target .work/fixed-frame-clear-combined-build-01/target, never clean. Build
floor max(14GiB,8GiB+2*allocated target); replay12GiB; child/closure8GiB. Freeze
sources until closure, preserve failures, no automatic retry, peer/process
changes, subagents or goal calls. This stage does not admit a runtime candidate.
