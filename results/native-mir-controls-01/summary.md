# Native MIR controls

Runtime remains the main deficit on these compute-heavy workflows. Inspect direct guest-call transitions before another engine change; the MIR-matched native control is retained.

| Workflow | Standard native / matching-MIR native / JIT median command (s) | Matching-MIR native vs standard (ms) | JIT vs matching-MIR native (ms) |
|---|---:|---:|---:|
| [folded-literal-trie](../native-mir-controls-folded-literal-trie-01/summary.md) | 1.649 / 1.642 / 2.824 | -23.4 | +1198.7 |
| [pgrust-sha1-inline8](../native-mir-controls-pgrust-sha1-inline8-01/summary.md) | 0.733 / 0.668 / 0.902 | -61.3 | +238.5 |

The JIT loses all ten paired edited commands to each native configuration. Matching-MIR native wins eight of ten against standard native. Paired differences and independent medians need not agree; five edits per workload do not establish statistical significance.

Both workloads retain their exact tests, and all three modes reject the deliberately wrong production edit. All fourteen JIT artifacts match the preceding retained build. All 28 native executable snapshots and the artifact/source/tool hashes were verified.

The matching native configuration uses MIR level 3 and thresholds 400/800/240 for target crates, with an explicit host target. Both native modes retain their Cargo test profiles. This matches target MIR policy; native std/libtest and the custom std-MIR/direct-entry build graphs differ.

| Workflow | JIT Cargo / execution median (s) | Native / matching-MIR libtest runtime (s, rounded by libtest) |
|---|---:|---:|
| folded-literal-trie | 0.836 / 1.892 | 0.32 / 0.23 |
| pgrust-sha1-inline8 | 0.466 / 0.375 | 0.10 / 0.03 |

Native libtest reports rounded test execution time and excludes process startup; the JIT execution stage includes its VM process and code generation. These stage numbers locate a large runtime deficit without providing an exact apples-to-apples CPU profile. The primary comparison remains the full edited command.

Cold samples and every raw command are linked in the per-workflow reports. Standard native remains a control; this experiment does not find the best available native development configuration. Whole applications remain unsupported.
