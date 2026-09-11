# JIT assertions: production-edit regression

All nine workflows pass with one frozen tool build: five cumulative production refactors, unchanged original test source, wrong-edit rejection in every mode, and restored source pins. The custom emitter now handles assertion conditions in generated regions. Performance qualification remains pending because the default word64 interpreter became slower in this run.

| Workflow | Native | Interpreter | JIT |
|---|---:|---:|---:|
| [fre-word64](../e2e-workflow-fre-word64-jit-assertions-01/summary.md) | 1.647 s | 17.879 s | 3.034 s |
| [pgrust](../e2e-workflow-pgrust-jit-assertions-01/summary.md) | 0.641 s | 0.785 s | 0.546 s |
| [fre-class-sequence](../e2e-workflow-fre-class-sequence-jit-assertions-01/summary.md) | 1.398 s | 0.736 s | 0.718 s |
| [nushell](../e2e-workflow-nushell-jit-assertions-01/summary.md) | 0.629 s | 0.435 s | 0.431 s |
| [ruff](../e2e-workflow-ruff-jit-assertions-01/summary.md) | 5.830 s | 3.087 s | 3.060 s |
| [rg-aot](../e2e-workflow-rg-aot-jit-assertions-01/summary.md) | 0.550 s | 0.192 s | 0.194 s |
| [nushell-type-relations](../e2e-workflow-nushell-type-relations-jit-assertions-01/summary.md) | 14.264 s | 8.504 s | 7.985 s |
| [fre-word64-inline8](../e2e-workflow-fre-word64-inline8-jit-assertions-01/summary.md) | 2.980 s | 15.638 s | 2.806 s |
| [pgrust-sha1-inline8](../e2e-workflow-pgrust-sha1-inline8-jit-assertions-01/summary.md) | 0.771 s | 6.032 s | 1.197 s |

Complete edit-to-test command medians include Cargo, strict checking, export, launch, and execution. These are focused existing tests in larger workspaces, not full applications or suites. Explicit MIR inlining retains development checks. Cold commands and stage medians are in the JSON; metadata-sysroot commands exclude the separately recorded 10.997 s reusable setup.

All 58 bytecode tests, 23,277 native differential/rejection commands, and 93 launcher checks pass. Five alternating identical-bytecode JIT pairs measured 1.574 to 1.526 s for eightfold word64 and 0.696 to 0.656 s for SHA-1, both winning all five pairs; default word64 was essentially flat. Total instruction counts and peak guest memory stayed identical.

Default word64 interpretation rose from 16.69 to 17.88 s per complete command in the first production comparison, with identical final bytecode. Execution rose from 15.87 to 17.07 s while Cargo stayed near 0.77 s. That requires a controlled interpreter comparison before this candidate is accepted. No performance regression is dismissed as noise, and no causal diagnosis is claimed yet.

[Validation and raw evidence](../jit-assertions-validation-01.json), [paired JIT runtime](../jit-assertions-runtime-01/summary.md).

Three alternating interpreter pairs confirm a regression on identical bytecode: word64 measured 15.803 → 17.056 s, and SHA-1 5.326 → 5.562 s. The candidate lost all three pairs in both workloads, with identical instruction counts and guest memory. This version is not retained as-is. The next experiment moves error formatting out of the inlined JIT transition; an engine-specific loop specialization is a separate alternative.
