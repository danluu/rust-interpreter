# Compute-heavy integration edits remain slower than native

The custom command takes 2.678× native wall time and 1.860× child CPU at the
median paired ratio. All original assertions and wrong-edit controls pass their
expected outcomes; the descriptive 0.90 wall-ratio target fails. No retry is
planned to change this decision.

| Median over five production edits | Seconds |
| --- | ---: |
| Native Cargo test | 1.449 |
| Custom check/export/JIT | 3.867 |
| Independent Cargo check | 0.529 |
| Custom Cargo stage | 0.772 |
| Custom execution stage | 3.014 |
| Native libtest suite, rounded | 0.43 |

Both original es8i tests execute 345,372 exhaustive/seeded/window comparisons.
Native uses default test threads; custom runs the bodies sequentially. This is
the actual command comparison, not equal parallelism or a pure compiler-speed
measurement. All modes use 18 build jobs, warm primed caches, O0/incremental and
repository debuginfo. Custom uses the retained compiler/runtime and explicit
qualified MIR, call, register, instruction and allocation options.

Every edit rebuilt the production library. After restoration, native, custom
and check all rebuilt the original source, and both executions passed. All 24
commands, 48 output logs, eight bytecode snapshots and frozen inputs verify.
The first short integration pilot's 20.4% gain does not generalize to this case.

Execution is the next bottleneck. The [owned-process profile](../fre-integration-es8-sample-01/assessment.md)
places most time in generated code, including substantial frame clearing. The
next bounded experiment should test frame-initialization proof coverage before
changing runtime behavior. [Summary](summary.json) · [Protocol](../../benchmarks/experiments/test-targets/ES8.md).
