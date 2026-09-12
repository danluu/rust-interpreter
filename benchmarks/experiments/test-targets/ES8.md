# Compute-heavy integration edit comparison

Run both original `es8i_semantic_proof` tests: 320,796 exhaustive comparisons
and 24,576 seeded/window comparisons. Their source and assertions stay unchanged.
Change only `ForwardAnchoredPlan::preflight_with_run_scanner` in the production
`forward_anchored.rs`. Five cumulative edits reverse an equivalent comparison,
reorder pure checks, and commute checked additions and a minimum. A wrong
prefilter bound must fail the existing accounting assertions in native and JIT
execution while passing ordinary Rust checking.

Use the normal root launcher, retained compiler/runtime, and the existing shared
integration cache. Native and check reuse separate completed caches. All modes
use 18 jobs; native uses repository full/unpacked debuginfo, O0/incremental and
default test threads. Preserve the qualified guest limits and MIR/JIT options.
Rotate native/custom/check order over five edited pairs. Record complete command
wall time, child CPU, Cargo/check stages, native suite time and guest execution.

The descriptive pilot target stays custom/native wall <= 0.90; CPU is reported.
This is a new workload comparison, not a runtime retention gate. No cold,
unchanged-build or whole-suite speed claim. Do not retry to turn a loss into a
win. A loss directs profiling toward the measured execution/export stage.

Require actual recompilation on every edit. After restoring the original with
the fixed helper, run all three modes again and require recompilation and the
original assertion outcomes. These three restoration controls are excluded from
timing. Preserve all 24 commands and eight guest snapshots. Admit at least
512MiB of growth above the 8GiB floor before starting source edits.
