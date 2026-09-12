# Inline the complete checked scalar memory path

Fixed before edits/builds/timing. Baseline remains qualified f33b40d same-frame-vm,
SHA25635a958ab46e28ed8cb56eaa038c0753f4590521405419df0dc862293d98a3e59.
Scalar-only candidate2a976e5 is parked after regressions; its gates/failure remain.
Its assembly showed load/store inlining moved the remaining call boundary to range.

This distinct implementation applies inline(always) to Memory::range as well as
load/store; read is already inline(always). Change attributes only, preserving
all method bodies, bounds, read-only/width checks, generic fallbacks and errors.
No unsafe, local-PC, validated-access helper, API, bytecode or guest-specific change.
Inspect resulting hot paths for actual range/load/store call/result-traffic removal,
code-size and spill changes. The compiler may expose further tradeoffs; do not
infer performance from assembly alone. Range's other callers must retain semantics.

Use the same prospective5% meaningful-gain gate on pgrust OR Ruff interpreter
median paired wall versus the best same-frame baseline. Neither compute case may
regress >5% wall/CPU. Six alternating pairs after a warmup pair on fixed six public
cases. JIT rejects wall/CPU regressions exceeding both5% paired median and5ms
absolute median difference. If passing, run fixed five additional cases with that
guard in both engines, plus ten native-oracle fixtures for correctness. Match all
stdout/instructions/peak memory and frozen inputs. No unchanged failed candidate
is rerun to cross a threshold; earlier failed implementations remain preserved.

All297 existing workspace tests must pass debug/release (one ignored), including
all scalar sizes/alignments/arenas/boundaries, copy/fill/random/allocation users of
range, errors/budgets and native/TLS paths. No new tests for unchanged semantics.
Qualify saved-bytecode process runtime including startup only. Whole edit/build/
test and unknown holdouts remain unmeasured. Serialize builds/tests/benchmarks on
original benchmark.lock; do not alter unrelated workloads/worktrees/caches.
