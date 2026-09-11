# Bulk initialization E2E result

Source `001065a` / tool `78e60cdd` improves complete edited commands by
**19.51% paired for folded and 19.95% for token** against the original b2 baseline.
CPU improves 20.60% and 20.54%. Folded passes its original 10% target. Token's
paired ratio is **0.8004639304**, just above the required 0.8, so its numerical
gate and the combined primary gate fail. Do not round this into a pass.

| Workload | Native command | Baseline JIT | Bulk-initialization candidate | Median paired change |
| --- | ---: | ---: | ---: | ---: |
| folded-literal-trie | 1.725 s | 2.544 s | 2.065 s | −19.51% |
| token-phrase | 2.246 s | 6.765 s | 5.421 s | −19.95% |

Command columns are marginal medians over fifteen edited commands per mode;
change is the median within-edit candidate/baseline ratio. Median paired wall
differences are −492 ms folded and −1.366 s token, with CPU differences −511 ms
and −1.352 s. Native remains faster on both workflows.

Folded VM execution medians are 1.580 s baseline / 1.062 s candidate; Cargo/export
is 0.874 / 0.935 s. Token execution is 5.150 / 3.824 s; Cargo/export is 1.521 /
1.475 s. Separate stage medians do not add to command medians. The preceding
resumable tool improved folded 10.6% and token 15.0% in a separate run. Subtracting
those experiments does not isolate the causal contribution of bulk clearing.

All **168 commands** completed: 126 primary and 42 independent Cargo-check
controls. Thirty edited pairs and 84 custom artifacts were reverified. Paired
bytecode is identical, recorded options match commands/launcher receipts,
original assertions/test sources remain unchanged, and wrong edits fail as
expected. All five owned source pins and restoration were verified. No samples
were discarded. Both fre workflows retain unresolved cross-history layout
changes; paired identity does not establish cross-history semantic equivalence.

Native uses root O0/incremental, 18 jobs and default libtest concurrency; custom
uses four jobs and the frozen per-workflow settings. Package overrides remain;
this is not a fastest-native claim. Limits, including token's 150,000 allocation
allowance, remain unchanged. Toolchain/dependency/std-MIR setup is excluded,
OS caches were not cleared, and unrelated work was left alone.

The candidate passes 257 workspace tests in debug/release, twelve CLI checks
and both original-artifact checks. Seven held-out workflows and broader native/
TLS/fre qualification have not run on it; older large-project evidence does not
transfer. The mode remains experimental and disabled by default.

Token misses its target by 0.0464 percentage points. That is too fine a distinction
to choose another runtime change without examining repeatability. Run exactly
one additional three-cycle comparison with the same binaries and controls,
retain both standalone gate decisions and report both sets of pairs. A later
pass cannot erase this failure; disagreement means threshold classification is
unstable. Do not repeat until a desired answer appears or invent a pooled
retention rule after seeing the new result.

[Gate calculations](gate-evaluation.json) · [Final verification](final-verification.json) ·
[Replication protocol](../../benchmarks/experiments/resumable-native-calls/REPLICATION.md) ·
[Folded report](../resumable-bulk-e2e-01-folded-literal-trie/summary.json) ·
[Token report](../resumable-bulk-e2e-01-token-phrase/summary.json)
