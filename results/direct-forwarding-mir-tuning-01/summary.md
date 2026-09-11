# MIR tuning with the same custom JIT

On seventeen unchanged original fre tests, MIR3 with an eightfold inlining budget wins all five production-edit comparisons against both ordinary MIR3 and native Rust. Median complete-command times are **1.237 s tuned JIT, 1.930 s ordinary MIR3 JIT, and 1.529 s native**. The paired median saving is 778 ms versus ordinary MIR3 and 293 ms versus native.

| Comparison | Native median (s) | Baseline JIT (s) | Tuned JIT (s) | Paired command saving (ms) | Wins vs baseline / native |
|---|---:|---:|---:|---:|---:|
| [MIR1 → MIR3](../paired-direct-forwarding-tls-mir3-01/summary.md) | 1.433 | 1.983 | 1.887 | 61.604 | 5/5 / 0/5 |
| [MIR3 → MIR3, inline budget ×8](../paired-direct-forwarding-tls-mir-inline8-01/summary.md) | 1.529 | 1.930 | 1.237 | 778.277 | 5/5 / 5/5 |

The larger budget sets `-Zmir-opt-level=3 -Zinline-mir-threshold=400 -Zinline-mir-hint-threshold=800 -Zinline-mir-forwarder-threshold=240`. Both custom modes use the same immutable VM and exporter, bounded bytecode leaf inlining, and explicit normal-return try callbacks. Ordinary type and borrow checking remain enabled; actual unwinding remains unsupported. Guest execution and native emission use the project’s own engine.

Each comparison includes fresh independent build caches, native controls, a deliberately incorrect production edit rejected by every mode, and five valid production edits. Original tests and tracing instrumentation remain unchanged. All seven baseline artifacts in the first comparison exactly match the prior default artifacts; all seven in the second match the preceding MIR3 artifacts. The two comparisons occurred separately: their savings are not added into a synthetic combined result.

MIR3 alone saves 62 ms per edited command but still loses every comparison with native. The larger inlining budget saves about 733 ms in guest execution per paired median. Its recorded cold command takes 5.689 s, compared with 6.148 s for ordinary MIR3 and 7.017 s native in that run. Cold costs, every pair and mode order remain in the linked reports. Five pairs on a shared host do not establish confidence intervals.

This is one production-edit workload. The completed wider survey lowers all389
original fre bodies in25 bounded batches:320 pass in the JIT,62 reach its16MiB
native-code cap, and7 remain ignored. All382 ordinary native controls pass.
Own-interpreter diagnostics add50 passes among those62;11 hit a smaller instruction
budget and one hits the live-allocation count cap. Every prior passing body is
preserved. Broader production-edit comparisons remain pending, and MIR defaults
remain unchanged. The forwarding corpus retains Ruff and larger Nushell compilation
regressions. [Full coverage and remaining limits](../audit-execution-fre-mir-inline8-01/summary.md).

[Forwarding corpus and limitations](../paired-direct-forwarding-corpus-01/summary.md).
