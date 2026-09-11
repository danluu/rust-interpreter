# Proven call-argument copies: production-edit qualification

A checked bytecode proof identifies direct calls whose arguments all lie inside the active caller frame. Those calls use safe slice copies after the same frame reservation and memory-limit checks. Other calls and all returns retain the existing copy path. The selected application is `both_engines`: The broader shortcut wins all six JIT pairs in each workload, has lower interpreter medians than baseline, and outperforms the JIT-only variant. JIT-only caused a clear word64 interpreter regression and is rejected.

All nine workflows pass on one frozen build, with five production edits, unchanged original tests, wrong-edit rejection in all modes, and restored source pins.

| Workflow | Native | Interpreter | JIT |
|---|---:|---:|---:|
| [fre-word64](../e2e-workflow-fre-word64-call-copy-01/summary.md) | 2.107 s | 15.776 s | 3.079 s |
| [pgrust](../e2e-workflow-pgrust-call-copy-01/summary.md) | 0.661 s | 0.758 s | 0.532 s |
| [fre-class-sequence](../e2e-workflow-fre-class-sequence-call-copy-01/summary.md) | 1.474 s | 0.786 s | 0.809 s |
| [nushell](../e2e-workflow-nushell-call-copy-01/summary.md) | 0.635 s | 0.432 s | 0.442 s |
| [ruff](../e2e-workflow-ruff-call-copy-01/summary.md) | 5.820 s | 3.057 s | 3.045 s |
| [rg-aot](../e2e-workflow-rg-aot-call-copy-01/summary.md) | 0.558 s | 0.203 s | 0.203 s |
| [nushell-type-relations](../e2e-workflow-nushell-type-relations-call-copy-01/summary.md) | 17.352 s | 8.064 s | 7.927 s |
| [fre-word64-inline8](../e2e-workflow-fre-word64-inline8-call-copy-01/summary.md) | 2.968 s | 13.886 s | 2.979 s |
| [pgrust-sha1-inline8](../e2e-workflow-pgrust-sha1-inline8-call-copy-01/summary.md) | 0.750 s | 5.245 s | 1.160 s |

Complete commands include Cargo, strict checking, export, launch, and execution. Cold commands and stage medians are retained in JSON. The metadata-sysroot workflows exclude the separately recorded 10.997 s reusable setup. Explicit MIR inlining retains development checks.

| Identical bytecode / engine | Baseline | Both engines | JIT only | Selected wins vs baseline |
|---|---:|---:|---:|---:|
| jit/word64-default | 2.282 s | 2.171 s | 2.209 s | 6/6 |
| jit/word64-inline8 | 1.528 s | 1.467 s | 1.483 s | 6/6 |
| jit/sha1-inline8 | 0.663 s | 0.643 s | 0.656 s | 6/6 |
| interpreter/word64-default | 14.911 s | 14.775 s | 16.051 s | 4/6 |
| interpreter/sha1-inline8 | 4.896 s | 4.738 s | 4.955 s | 6/6 |

Each workload/engine comparison uses all six execution orders once. All 90 commands succeed. Within each matched workload and engine, the three builds agree on output, virtual instructions, emitted code, and guest memory use. The selected build also passes 65 bytecode tests, 40 explicit-result old/new VM fixture commands, 23,277 native differential/rejection commands, and 93 launcher checks. Historical command medians include host and compiler variation; the controlled comparisons isolate the runtime implementation more closely.

[Proof and boundary cases](../call-local-copy-proof-01/summary.md), [selected validation](../call-local-copy-validation-01.json).
