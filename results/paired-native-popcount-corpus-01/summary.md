# Native population count: twelve production-edit workflows

The candidate wins **37/60** complete edited-command pairs against the prior custom JIT. Native wins 16/60 comparisons against the candidate. All selected original tests pass, all modes reject the deliberately wrong edit, and all five source checkouts are restored.

| Workflow | Native median (s) | Prior JIT (s) | Candidate JIT (s) | Paired command change (ms) | Paired execution change (ms) | Wins |
|---|---:|---:|---:|---:|---:|---:|
| [fre-folded-literal-trie](../e2e-paired-fre-folded-literal-trie-native-popcount-01/summary.md) | 2.052 | 3.864 | 3.866 | +1.710 | -20.730 | 2/5 |
| [fre-word64](../e2e-paired-fre-word64-native-popcount-01/summary.md) | 1.659 | 2.299 | 2.292 | -34.998 | -2.919 | 3/5 |
| [fre-word64-inline8](../e2e-paired-fre-word64-inline8-native-popcount-01/summary.md) | 2.160 | 2.034 | 2.000 | -32.889 | -1.798 | 4/5 |
| [pgrust-sha1-inline8](../e2e-paired-pgrust-sha1-inline8-native-popcount-01/summary.md) | 0.799 | 0.941 | 0.921 | -27.003 | -18.845 | 5/5 |
| [pgrust](../e2e-paired-pgrust-native-popcount-broad-01/summary.md) | 0.658 | 0.516 | 0.509 | -2.339 | +0.000 | 3/5 |
| [fre-class-sequence](../e2e-paired-fre-class-sequence-native-popcount-broad-01/summary.md) | 1.534 | 0.916 | 0.934 | -18.072 | +0.035 | 3/5 |
| [nushell](../e2e-paired-nushell-native-popcount-broad-01/summary.md) | 0.646 | 0.457 | 0.449 | -2.506 | -0.007 | 3/5 |
| [ruff](../e2e-paired-ruff-native-popcount-broad-01/summary.md) | 5.669 | 3.079 | 3.134 | +12.417 | -0.138 | 2/5 |
| [rg-aot](../e2e-paired-rg-aot-native-popcount-broad-01/summary.md) | 0.546 | 0.208 | 0.200 | -9.990 | +0.239 | 3/5 |
| [nushell-type-relations](../e2e-paired-nushell-type-relations-native-popcount-broad-01/summary.md) | 11.510 | 6.797 | 6.651 | -611.649 | +0.051 | 3/5 |
| [fre-grapheme-scalar-dfa](../e2e-paired-fre-grapheme-scalar-dfa-native-popcount-broad-01/summary.md) | 1.888 | 1.135 | 1.135 | -7.560 | -0.374 | 3/5 |
| [fre-packed-literal-set](../e2e-paired-fre-packed-literal-set-native-popcount-broad-01/summary.md) | 2.335 | 1.283 | 1.260 | -33.285 | +0.233 | 3/5 |

The custom AArch64 JIT now emits population count through 64 bits. All 128-bit counts retain the custom interpreter path. Bytecode, frames, guest instruction counts and frontend options are unchanged. Strict type and borrow checking remains enabled.

The VM differs; the exporter binaries are byte-for-byte identical. All sixty executed bytecode pairs are identical and their hashes are rechecked. A separate six-pair runtime screen for each of the four compute workflows compares both VMs on the same retained artifacts. Complete-command measurements also include Cargo and export, where variation can dominate a small execution gain.

Every timing, mode order, source edit, artifact hash and cold/setup cost is retained in the linked reports. All artifact identity flags were rechecked against the retained files. Five pairs per workflow on a shared host do not establish confidence intervals. Separate stage medians need not add to the command median. No A/A median is subtracted and no outlier is discarded.

Commands include Cargo, strict checking, export, launch, JIT construction and original-test execution. Downloads, tool bootstrap and reusable standard-library MIR setup are outside the timers. The complete eighteen-test folded-trie suite is included; these selected workflows are not whole-application support. Fresh native controls preserve all 303 passing fre tests and all 389 classifications. The full twelve-workflow corpus is complete.

[Identical-artifact runtime screen](../native-popcount-real-screen-01/summary.md), [broad native correctness](../native-popcount-default-validation-01.json), [identical-tool calibration](../identical-tools-aa-e2e-01/summary.md).

The twelve-workflow result does not establish a broad command-speed gain from
population count. SHA-1 improves all five edited execution stages and commands;
most other apparent command savings occur outside execution. Ruff retains a 12 ms
paired command regression. Larger Nushell ranges from 2.876 seconds faster to
2.322 seconds slower, with a 0.051 ms median execution increase. The earlier
identical-tool calibration is retained as evidence of variation, not subtracted.

Decision: retain the correct, general opcode support as an experimental baseline
for the next separately measured change. All 303 previously passing fre tests and
all 389 classifications survive fresh native controls. Next, test direct dispatch
of the interpreted continuation after a successful native exit. The current engine
remains byte-for-byte frozen until that experiment is explicitly built.
[Decision record](decision.json), [fresh coverage](../audit-execution-fre-native-popcount-01/summary.md).
