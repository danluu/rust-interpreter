# Direct dispatch after native exits: four production-edit workflows

The candidate wins **20/20** complete edited-command pairs against the prior custom JIT. Native wins 18/20 comparisons against the candidate. All selected original tests pass, all modes reject the deliberately wrong edit, and both source checkouts are restored.

| Workflow | Native median (s) | Prior JIT (s) | Candidate JIT (s) | Paired command change (ms) | Paired execution change (ms) | Wins |
|---|---:|---:|---:|---:|---:|---:|
| [fre-folded-literal-trie](../e2e-paired-fre-folded-literal-trie-native-exit-dispatch-01/summary.md) | 1.854 | 3.597 | 3.494 | -94.142 | -75.305 | 5/5 |
| [fre-word64](../e2e-paired-fre-word64-native-exit-dispatch-01/summary.md) | 1.723 | 2.272 | 2.179 | -67.853 | -59.952 | 5/5 |
| [fre-word64-inline8](../e2e-paired-fre-word64-inline8-native-exit-dispatch-01/summary.md) | 1.559 | 1.713 | 1.643 | -58.480 | -26.990 | 5/5 |
| [pgrust-sha1-inline8](../e2e-paired-pgrust-sha1-inline8-native-exit-dispatch-01/summary.md) | 0.734 | 0.921 | 0.913 | -9.011 | -4.609 | 5/5 |

After a successful native exit, the VM checks the remaining budget and dispatches the interpreted continuation directly. Native successors are already linked; the previous loop repeated its header and JIT lookup before the same interpreted operation. Bytecode, frames and frontend options remain unchanged, with strict type and borrow checking.

Both actual VM and exporter binaries differ. All twenty executed bytecode pairs are identical and their hashes are rechecked. A separate six-pair runtime screen per workflow compares both VMs on the same retained artifacts and verifies identical guest instruction totals, memory peaks, generated-code sizes and full per-PC profiles. Complete-command measurements also include Cargo and export, where variation can dominate a small execution gain.

Every timing, mode order, source edit, artifact hash and cold/setup cost is retained in the linked reports. All artifact identity flags were rechecked against the retained files. Five pairs per workflow on a shared host do not establish confidence intervals. Separate stage medians need not add to the command median. No A/A median is subtracted and no outlier is discarded.

Commands include Cargo, strict checking, export, launch, JIT construction and original-test execution. Downloads, tool bootstrap and reusable standard-library MIR setup are outside the timers. The complete eighteen-test folded-trie suite is included; these selected workflows are not whole-application support. The fresh 389-case fre survey and broader project corpus remain separate qualification steps.

[Identical-artifact runtime screen](../native-exit-dispatch-real-screen-01/summary.md), [broad native correctness](../native-exit-dispatch-default-validation-01.json), [identical-tool calibration](../identical-tools-aa-e2e-01/summary.md).
