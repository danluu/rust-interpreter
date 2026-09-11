# Medium aggregate leaf inlining: four production-edit workflows

The candidate wins **12/20** complete edited-command pairs against the prior custom JIT. Native wins 15/20 comparisons against the candidate. All selected original tests pass, all modes reject the deliberately wrong edit, and both source checkouts are restored.

| Workflow | Native median (s) | Prior JIT (s) | Candidate JIT (s) | Paired command change (ms) | Paired execution change (ms) | Wins |
|---|---:|---:|---:|---:|---:|---:|
| [fre-folded-literal-trie](../e2e-paired-fre-folded-literal-trie-native-medium-leaf-01/summary.md) | 1.759 | 3.693 | 3.765 | +128.160 | +33.392 | 1/5 |
| [fre-word64](../e2e-paired-fre-word64-native-medium-leaf-01/summary.md) | 2.090 | 2.496 | 2.539 | -19.540 | -9.767 | 3/5 |
| [fre-word64-inline8](../e2e-paired-fre-word64-inline8-native-medium-leaf-01/summary.md) | 2.047 | 1.902 | 1.889 | -54.205 | -5.157 | 4/5 |
| [pgrust-sha1-inline8](../e2e-paired-pgrust-sha1-inline8-native-medium-leaf-01/summary.md) | 0.755 | 1.000 | 0.975 | -22.252 | -10.215 | 4/5 |

The wrapper stopped after all four benchmark subprocesses completed because it incorrectly required every pair to have different bytecode. Per-workflow reports, artifact hashes and restored source pins were subsequently verified; no timing was rerun or discarded.

The opt-in leaf inliner accepts fixed body, argument and result copies up to 128 bytes, with the existing frame and code-growth limits. Both builds use identical VM binaries, strict frontend checking, guest MIR options and leaf-inlining settings. The fifteen fre artifact pairs change as additional calls are inlined and caller frames grow. All five SHA-1 pairs are byte-identical, so their timing differences are not evidence of an execution-code improvement. Command times include Cargo, checking, export, launch, JIT construction and original-test execution.

Every timing, mode order, source edit, artifact hash and cold/setup cost is retained in the linked reports. Five pairs per workflow on a shared host do not establish confidence intervals. Separate stage medians need not add to the command median. The full eighteen-test folded-trie suite is included; these selected tests are not complete application support.

[Runtime screen](../native-medium-leaf-real-screen-01/summary.md), [broad native correctness](../native-medium-leaf-default-validation-01.json).
