# Direct dispatch after native exits: twelve production-edit workflows

The candidate wins **39/60** complete edited-command pairs against the prior custom JIT. Native wins 18/60 comparisons against the candidate. All selected original tests pass, all modes reject the deliberately wrong edit, and all five source checkouts are restored.

| Workflow | Native median (s) | Prior JIT (s) | Candidate JIT (s) | Paired command change (ms) | Paired execution change (ms) | Wins |
|---|---:|---:|---:|---:|---:|---:|
| [fre-folded-literal-trie](../e2e-paired-fre-folded-literal-trie-native-exit-dispatch-01/summary.md) | 1.854 | 3.597 | 3.494 | -94.142 | -75.305 | 5/5 |
| [fre-word64](../e2e-paired-fre-word64-native-exit-dispatch-01/summary.md) | 1.723 | 2.272 | 2.179 | -67.853 | -59.952 | 5/5 |
| [fre-word64-inline8](../e2e-paired-fre-word64-inline8-native-exit-dispatch-01/summary.md) | 1.559 | 1.713 | 1.643 | -58.480 | -26.990 | 5/5 |
| [pgrust-sha1-inline8](../e2e-paired-pgrust-sha1-inline8-native-exit-dispatch-01/summary.md) | 0.734 | 0.921 | 0.913 | -9.011 | -4.609 | 5/5 |
| [pgrust](../e2e-paired-pgrust-native-exit-dispatch-broad-01/summary.md) | 0.669 | 0.511 | 0.509 | -5.207 | -0.683 | 3/5 |
| [fre-class-sequence](../e2e-paired-fre-class-sequence-native-exit-dispatch-broad-01/summary.md) | 1.301 | 0.734 | 0.755 | +21.392 | +0.145 | 2/5 |
| [nushell](../e2e-paired-nushell-native-exit-dispatch-broad-01/summary.md) | 0.650 | 0.434 | 0.432 | -0.585 | +0.116 | 3/5 |
| [ruff](../e2e-paired-ruff-native-exit-dispatch-broad-01/summary.md) | 5.860 | 3.074 | 3.174 | +179.608 | -2.064 | 2/5 |
| [rg-aot](../e2e-paired-rg-aot-native-exit-dispatch-broad-01/summary.md) | 0.559 | 0.193 | 0.194 | +2.919 | +0.136 | 2/5 |
| [nushell-type-relations](../e2e-paired-nushell-type-relations-native-exit-dispatch-broad-01/summary.md) | 11.650 | 6.269 | 6.582 | +383.424 | +0.194 | 1/5 |
| [fre-grapheme-scalar-dfa](../e2e-paired-fre-grapheme-scalar-dfa-native-exit-dispatch-broad-01/summary.md) | 2.279 | 1.371 | 1.025 | -102.691 | -0.540 | 4/5 |
| [fre-packed-literal-set](../e2e-paired-fre-packed-literal-set-native-exit-dispatch-broad-01/summary.md) | 1.388 | 0.897 | 0.882 | +2.018 | -0.725 | 2/5 |

After a successful native exit, the VM checks the remaining budget and dispatches the interpreted continuation directly. Native successors are already linked; the previous loop repeated its header and JIT lookup before the same interpreted operation. Bytecode, frames and frontend options remain unchanged, with strict type and borrow checking.

Both actual VM and exporter binaries differ. All sixty executed bytecode pairs are identical and their hashes are rechecked. A separate six-pair runtime screen for each of the four compute workflows compares both VMs on the same retained artifacts. Complete-command measurements also include Cargo and export, where variation can dominate a small execution gain.

Every timing, mode order, source edit, artifact hash and cold/setup cost is retained in the linked reports. All artifact identity flags were rechecked against the retained files. Five pairs per workflow on a shared host do not establish confidence intervals. Separate stage medians need not add to the command median. No A/A median is subtracted and no outlier is discarded.

Commands include Cargo, strict checking, export, launch, JIT construction and original-test execution. Downloads, tool bootstrap and reusable standard-library MIR setup are outside the timers. The complete eighteen-test folded-trie suite is included; these selected workflows are not whole-application support. Fresh native controls preserve all 303 passing fre tests and all 389 classifications. The full twelve-workflow corpus is complete.

[Identical-artifact runtime screen](../native-exit-dispatch-real-screen-01/summary.md), [broad native correctness](../native-exit-dispatch-default-validation-01.json), [identical-tool calibration](../identical-tools-aa-e2e-01/summary.md).
