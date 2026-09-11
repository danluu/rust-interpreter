# Call-argument copies: choosing between two applications

The retained candidate applies a conservative local-frame copy proof to both interpreter and JIT calls. A variant that skipped the proof and shortcut in interpreter mode was slower. Both variants pass 65 bytecode tests, 40 old/new VM fixture commands, 23,277 native differential/rejection commands, and 93 launcher checks. All nine production-edit workflows now pass on the selected build.

| Workload / engine | Qualified baseline | Both engines | JIT only | Both vs baseline wins |
|---|---:|---:|---:|---:|
| jit/word64-default | 2.282 s | 2.171 s | 2.209 s | 6/6 |
| jit/word64-inline8 | 1.528 s | 1.467 s | 1.483 s | 6/6 |
| jit/sha1-inline8 | 0.663 s | 0.643 s | 0.656 s | 6/6 |
| interpreter/word64-default | 14.911 s | 14.775 s | 16.051 s | 4/6 |
| interpreter/sha1-inline8 | 4.896 s | 4.738 s | 4.955 s | 6/6 |

Every one of the six possible execution orders is used once for each workload and engine. All 90 commands succeed. Matched commands use identical bytecode and agree on instruction counts, emitted code, and peak guest memory. Initial two-build tests showed consistent JIT gains but small, mixed interpreter effects; that uncertainty motivated this balanced comparison. Raw samples and load records are retained.

The broader shortcut wins all six JIT pairs for every workload. Interpretation improves modestly for word64 (four of six pairs) and more consistently for SHA-1 (six of six). JIT-only loses every interpreter word64 pair against baseline, increasing its median from 14.91 to 16.05 seconds. It is rejected.

The selected VM binary is 764,944 bytes, 33,664 bytes larger than the baseline. The rejected JIT-only binary is smaller at 748,432 bytes. Read-only host disassembly confirms that the latter skips interpreter proof setup, but it does not establish the cause of its slowdown. The runtime measurements determine the selection.

These are complete VM process runs on saved production-test bytecode, including artifact loading, validation, proof setup, JIT construction when enabled, and execution. They exclude Cargo and source compilation; the fresh nine-workflow edit/build/test corpus has now passed. Cargo variation still obscures small runtime gains in historical complete-command comparisons.

[Qualified production corpus and stage medians](../e2e-call-copy-corpus-01/summary.md).

[Proof coverage and boundary cases](../call-local-copy-proof-01/summary.md), [selected validation](../call-local-copy-validation-01.json), [rejected variant validation](../call-local-copy-jit-only-validation-01.json).
