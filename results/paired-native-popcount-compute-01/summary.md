# Native population count: four production-edit workflows

The candidate wins **14/20** complete edited-command pairs against the prior custom JIT. Native wins 16/20 comparisons against the candidate. All selected original tests pass, all modes reject the deliberately wrong edit, and both source checkouts are restored.

| Workflow | Native median (s) | Prior JIT (s) | Candidate JIT (s) | Paired command change (ms) | Paired execution change (ms) | Wins |
|---|---:|---:|---:|---:|---:|---:|
| [fre-folded-literal-trie](../e2e-paired-fre-folded-literal-trie-native-popcount-01/summary.md) | 2.052 | 3.864 | 3.866 | +1.710 | -20.730 | 2/5 |
| [fre-word64](../e2e-paired-fre-word64-native-popcount-01/summary.md) | 1.659 | 2.299 | 2.292 | -34.998 | -2.919 | 3/5 |
| [fre-word64-inline8](../e2e-paired-fre-word64-inline8-native-popcount-01/summary.md) | 2.160 | 2.034 | 2.000 | -32.889 | -1.798 | 4/5 |
| [pgrust-sha1-inline8](../e2e-paired-pgrust-sha1-inline8-native-popcount-01/summary.md) | 0.799 | 0.941 | 0.921 | -27.003 | -18.845 | 5/5 |

The custom AArch64 JIT now emits population count through 64 bits. All 128-bit counts retain the custom interpreter path. Bytecode, frames, guest instruction counts and frontend options are unchanged. Strict type and borrow checking remains enabled.

The VM differs; the exporter binaries are byte-for-byte identical. All twenty executed bytecode pairs are identical and their hashes are rechecked. A separate six-pair runtime screen per workflow compares both VMs on the same retained artifacts. Complete-command measurements also include Cargo and export, where variation can dominate a small execution gain.

Every timing, mode order, source edit, artifact hash and cold/setup cost is retained in the linked reports. All artifact identity flags were rechecked against the retained files. Five pairs per workflow on a shared host do not establish confidence intervals. Separate stage medians need not add to the command median. No A/A median is subtracted and no outlier is discarded.

Commands include Cargo, strict checking, export, launch, JIT construction and original-test execution. Downloads, tool bootstrap and reusable standard-library MIR setup are outside the timers. The complete eighteen-test folded-trie suite is included; these selected workflows are not whole-application support. Fresh native controls now preserve all 303 passing fre tests and all 389 classifications. The broader project corpus remains a separate qualification step.

[Identical-artifact runtime screen](../native-popcount-real-screen-01/summary.md), [broad native correctness](../native-popcount-default-validation-01.json), [identical-tool calibration](../identical-tools-aa-e2e-01/summary.md).

Decision: continue experimental qualification. SHA-1 improves all five edited commands and execution stages. Word64 command gains are mostly in Cargo, and folded-trie remains mixed across the runtime and command comparisons. No broad speed claim is established. Fresh fre coverage passed; the larger-project corpus follows. [Decision record](decision.json).

[Fresh fre coverage](../audit-execution-fre-native-popcount-01/summary.md).
