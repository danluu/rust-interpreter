# Direct native local fills: production-edit comparison

The deterministic-exporter comparison wins 14 of 15 complete-command pairs on the three compute workflows. Native remains faster in each workflow. The remaining eight workflows and the fresh fre execution survey are separate qualification gates.

| Workflow | Native median (s) | Baseline JIT median (s) | Candidate JIT median (s) | Median paired change (ms) | Wins |
|---|---:|---:|---:|---:|---:|
| [fre-word64](../e2e-paired-fre-word64-jit-local-fill-02/summary.md) | 1.595244 | 2.424009 | 2.261908 | -162.878 | 5/5 |
| [fre-word64-inline8](../e2e-paired-fre-word64-inline8-jit-local-fill-02/summary.md) | 1.771961 | 1.892394 | 1.840050 | -80.999 | 4/5 |
| [pgrust-sha1-inline8](../e2e-paired-pgrust-sha1-inline8-jit-local-fill-02/summary.md) | 0.765022 | 0.983836 | 0.938357 | -41.253 | 5/5 |

These are five cumulative production-code refactors per workflow with the original tests unchanged. Native, baseline JIT and candidate JIT alternate order and use independent Cargo caches. Both custom modes enable the same opt-in leaf inliner; every paired executed bytecode artifact is byte-identical. Every mode rejects the deliberately wrong production edit. Full wall time includes Cargo, strict checking, export, transformation, loading, JIT construction and execution.

The execution stage improves in every pair. Median paired execution changes are −159 ms for word64, −61 ms for word64-inline8, and −41 ms for SHA-1. Median paired Cargo changes are −4 ms, −8 ms and approximately zero. The one non-winning inline8 pair differs by only +0.026 ms: its 37 ms execution reduction is offset by 38 ms more Cargo time. Cargo differences are retained and are not attributed to this runtime optimization. The median paired difference and the difference of the two medians are distinct statistics.

The baseline is immutable build 96de445; the candidate is 67a3a33. Both contain the deterministic function-pointer scheduling fix. Both binary manifests and all executed artifacts are retained by each workflow report. There is no guest LLVM or external interpreter fallback. The VMs are byte-identical to builds 4227fc and 2df145 respectively. The identical-artifact assertion isolates the emitted program after the exporter fix. Interpreter behavior is checked separately by the 96-command runtime screen.

Five samples per workflow on a shared host are not confidence intervals. Cold commands use empty per-mode caches but exclude downloads, tool bootstrap, OS cache coldness and shared standard-library MIR setup. No timing samples were excluded and no cleanup overlapped measurement.

[Exporter reproducibility fix](../export-determinism-01/summary.md). [Same-artifact runtime comparison](../jit-local-fill-runtime-01/summary.md), [correctness qualification](../export-order-validation-01.json).
