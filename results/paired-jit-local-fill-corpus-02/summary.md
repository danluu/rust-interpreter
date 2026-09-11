# Native local fills across eleven production-edit workflows

Retain direct native stores for small, proven local fills. The clearest benefit is in compute tests using the opt-in leaf inliner, which remains disabled by default. Both compared builds include deterministic function-pointer body scheduling, and every baseline/candidate artifact pair is byte-identical. All original tests and deliberately wrong production-edit controls pass their expected outcomes.

| Workflow | Native median (s) | Baseline JIT median (s) | Candidate JIT median (s) | Median paired change (ms) | Wins |
|---|---:|---:|---:|---:|---:|
| [fre-word64](../e2e-paired-fre-word64-jit-local-fill-02/summary.md) | 1.595244 | 2.424009 | 2.261908 | -162.878 | 5/5 |
| [fre-word64-inline8](../e2e-paired-fre-word64-inline8-jit-local-fill-02/summary.md) | 1.771961 | 1.892394 | 1.840050 | -80.999 | 4/5 |
| [pgrust-sha1-inline8](../e2e-paired-pgrust-sha1-inline8-jit-local-fill-02/summary.md) | 0.765022 | 0.983836 | 0.938357 | -41.253 | 5/5 |
| [pgrust](../e2e-paired-pgrust-jit-local-fill-broad-02/summary.md) | 0.648943 | 0.533282 | 0.525924 | -8.468 | 4/5 |
| [fre-class-sequence](../e2e-paired-fre-class-sequence-jit-local-fill-broad-02/summary.md) | 1.382393 | 0.757716 | 0.745830 | -8.730 | 4/5 |
| [nushell](../e2e-paired-nushell-jit-local-fill-broad-02/summary.md) | 0.669736 | 0.480484 | 0.475973 | -0.372 | 3/5 |
| [ruff](../e2e-paired-ruff-jit-local-fill-broad-02/summary.md) | 5.814827 | 3.037009 | 3.144080 | +54.898 | 2/5 |
| [rg-aot](../e2e-paired-rg-aot-jit-local-fill-broad-02/summary.md) | 0.540369 | 0.199015 | 0.193661 | -7.786 | 3/5 |
| [nushell-type-relations](../e2e-paired-nushell-type-relations-jit-local-fill-broad-03/summary.md) | 16.028388 | 7.503656 | 5.972561 | -1377.235 | 3/5 |
| [fre-grapheme-scalar-dfa](../e2e-paired-fre-grapheme-scalar-dfa-jit-local-fill-broad-03/summary.md) | 1.298316 | 0.818067 | 0.807759 | -12.155 | 4/5 |
| [fre-packed-literal-set](../e2e-paired-fre-packed-literal-set-jit-local-fill-broad-03/summary.md) | 1.518648 | 0.927959 | 0.918984 | +12.797 | 2/5 |

The candidate wins 39/55 complete-command pairs and 34/55 execution-stage pairs. The three compute workflows win 14/15 complete commands and all 15 execution comparisons: median paired full-command changes are −163 ms, −81 ms and −41 ms. The one compute loss is effectively tied at +0.026 ms. Native remains faster on these compute workflows. Short and frontend-heavy workflow timings must be read with their retained stage measurements; milliseconds of shared-host Cargo variation are not evidence of a runtime change.

Each workflow uses five cumulative production-body refactors, unchanged original tests, alternating mode order, and independent Cargo caches. Full timings include strict frontend checking, export, leaf inlining, loading, JIT construction and execution. All timing samples and executed bytecode are retained. Cold commands exclude downloads, tool bootstrap, OS-cache coldness and shared standard-library MIR installation. Five samples per workflow are not confidence intervals. Cleanup completed at explicit boundaries before measurement resumed.

Candidate build 67a3a33 contains the native-fill emitter and deterministic exporter. Baseline 96de445 has the same exporter fix and the earlier emitter. Their VM binaries exactly match 2df145 and 4227fc respectively, preserving the earlier 96-command same-artifact runtime evidence. That screen wins all 18 inlined-bytecode JIT pairs; three default-bytecode controls generate identical native-code sizes and execution counters, and interpreter controls show no consistent regression.

The original Ruff comparison stopped at its artifact-equality guard before any edited commands. Randomized scheduling of newly required function-pointer bodies changed function and constant layout. A focused regression test reproduced 12 different artifacts from 12 unchanged-source exports. Assigned-ID scheduling now gives one artifact across repeated exports in four configurations, with 926 negative-control/native comparison commands and another 674 commands for the corrected baseline. The failed cold comparison is preserved and is not included here.

The first Nushell type-relations run was interrupted when native rustc received SIGTERM on its second production edit; the sender is unknown. Its partial timings and diagnostics are retained separately and excluded from this table. The entire workflow was retried with fresh caches and a fresh run ID.

Correctness evidence includes the unchanged 88-test bytecode implementation, 24 option/cache/source-edit checks, 71 SIMD checks, 79 audit checks, 99 launcher checks, and 23,502 native differential/rejection commands with inlining disabled plus another 23,502 with it enabled. A fresh deterministic collection and execution survey matches native on all 231 supported ordinary fre tests; 158 remain lowering-blocked. These are selected workflows and supported ordinary bodies, not complete application or suite support.

[Compute comparison](../paired-jit-local-fill-e2e-02/summary.md), [runtime screen](../jit-local-fill-runtime-01/summary.md), [export-order fix](../export-determinism-01/summary.md), [correctness gates](../export-order-validation-01.json), [fresh fre survey](../audit-execution-fre-export-order-01/summary.md).
