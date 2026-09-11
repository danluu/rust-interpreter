# Direct native local fills: production-edit comparison

The candidate wins all 15 complete-command pairs on the three compute workflows. Native remains faster in each workflow. The remaining eight workflows and the fresh fre execution survey are separate qualification gates.

| Workflow | Native median (s) | Baseline JIT median (s) | Candidate JIT median (s) | Median paired change (ms) | Wins |
|---|---:|---:|---:|---:|---:|
| [fre-word64](../e2e-paired-fre-word64-jit-local-fill-01/summary.md) | 1.603527 | 2.422484 | 2.260501 | -152.627 | 5/5 |
| [fre-word64-inline8](../e2e-paired-fre-word64-inline8-jit-local-fill-01/summary.md) | 1.778707 | 1.942450 | 1.839338 | -125.666 | 5/5 |
| [pgrust-sha1-inline8](../e2e-paired-pgrust-sha1-inline8-jit-local-fill-01/summary.md) | 0.763263 | 1.000420 | 0.957498 | -44.320 | 5/5 |

These are five cumulative production-code refactors per workflow with the original tests unchanged. Native, baseline JIT and candidate JIT alternate order and use independent Cargo caches. Both custom modes enable the same opt-in leaf inliner; every paired executed bytecode artifact is byte-identical. Every mode rejects the deliberately wrong production edit. Full wall time includes Cargo, strict checking, export, transformation, loading, JIT construction and execution.

The execution stage improves in every pair. Median paired execution changes are −153 ms for word64, −75 ms for word64-inline8, and −36 ms for SHA-1. The latter two also have lower median Cargo time (−51 ms and −9 ms). Cargo differences are retained and are not attributed to this runtime optimization. The median paired difference and the difference of the two medians are distinct statistics.

The baseline is immutable build 4227fc; the candidate is 2df145. Both binary manifests and all executed artifacts are retained by each workflow report. There is no guest LLVM or external interpreter fallback. The exporter changes only through rebuilding the shared bytecode library; the identical-artifact assertion isolates the emitted program. Interpreter behavior is checked separately by the 96-command runtime screen.

Five samples per workflow on a shared host are not confidence intervals. Cold commands use empty per-mode caches but exclude downloads, tool bootstrap, OS cache coldness and shared standard-library MIR setup. No timing samples were excluded and no cleanup overlapped measurement.

[Same-artifact runtime comparison](../jit-local-fill-runtime-01/summary.md), [correctness qualification](../jit-local-fill-validation-01.json).
