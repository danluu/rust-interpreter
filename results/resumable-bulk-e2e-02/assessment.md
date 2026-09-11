# Unchanged-tool replication result

The single predeclared replication of `001065a` / tool `78e60cdd` improves
complete edited commands **19.15% paired for folded and 19.97% for token**
against the original b2 baseline. CPU improves 19.48% and 20.07%. Folded passes;
token's ratio **0.8003441753** remains above the original 0.8 maximum. Both
independent runs therefore fail the combined numerical gate. No rounding,
pooled retention rule or further repeated attempt is used.

| Workload | Native command | Baseline JIT | Candidate JIT | Median paired change |
| --- | ---: | ---: | ---: | ---: |
| folded-literal-trie | 1.852 s | 2.582 s | 2.085 s | −19.15% |
| token-phrase | 2.202 s | 7.161 s | 5.596 s | −19.97% |

Command columns are marginal medians; change is the median within-edit ratio.
Native remains faster on both. Folded execution medians are 1.569 / 1.068 s
baseline/candidate, with Cargo/export 0.932 / 0.961 s. Token execution is
5.568 / 4.097 s, with Cargo/export 1.479 / 1.446 s. These separate stage medians
do not add to complete-command medians.

All 168 commands completed, including 42 independent Cargo checks. Thirty
edited pairs and 84 custom artifacts were verified, with identical paired
bytecode, original assertions, rejected wrong edits and restored source pins.
Native uses root O0/incremental, 18 jobs and default libtest concurrency; custom
uses four jobs and the original workflow flags/limits. Manifest overrides remain;
this is not a fastest-native claim. Toolchain/dependency/std-MIR setup is excluded,
OS caches were not cleared and unrelated work was not controlled.

The [two-run report](../resumable-bulk-replication-01/assessment.md) preserves all
336 commands, 60 edited pairs and 168 artifacts, and gives per-edit wall/CPU
variation. Corresponding cache-history states have matching artifact hashes
across runs. Cross-cycle layout differences remain unresolved; matching these
histories does not prove general determinism or semantic equivalence.

The roughly 19–20% improvement repeated. Further repeated attempts or small
batch-size tuning would add less useful information than broader compatibility
checks. Next qualify this experimental candidate with the full native differential
validator, TLS/destructor suite, fre body replay and held-out large-project edit
workflows. This characterizes the candidate; it does not waive the failed gate,
change defaults, transfer older coverage or establish large-codebase readiness.

[Gate calculations](gate-evaluation.json) · [Final verification](final-verification.json) ·
[Replication protocol](../../benchmarks/experiments/resumable-native-calls/REPLICATION.md)
