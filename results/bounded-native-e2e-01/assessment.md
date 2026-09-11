# Bounded native call-tree result

Experimental source `09de2a9` / tool `c98d995b` makes token phrase faster, but
**misses both predeclared performance gates**. Keep the option experimental and
disabled by default. Next move the remaining outer Calls into ordinary generated
regions; do not promote this intermediate result to large-codebase readiness.

| Workload | Native command | Baseline JIT | Native-call candidate | Median paired change |
| --- | ---: | ---: | ---: | ---: |
| folded-literal-trie | 1.681 s | 2.559 s | 2.603 s | +3.0% |
| token-phrase | 1.968 s | 6.504 s | 5.565 s | -14.4% |

Command columns are medians over fifteen edited commands per mode. The change
column is the median of within-edit candidate/baseline ratios, so it is not the
ratio of the two marginal medians. The target was at least 20% lower paired token
latency and 10% lower folded latency, with CPU improving too. Measured paired
CPU changes are −14.4% token and +2.0% folded. Median paired wall differences are
−945 ms token and +73 ms folded. Neither improvement target was reached.

Token execution medians fell from 5.111 to 4.187 s; Cargo/export medians were
1.312 and 1.293 s. Folded execution rose from 1.578 to 1.644 s; Cargo/export
medians were 0.891 and 0.880 s. Separate stage medians are descriptive and do not
add to the complete-command medians. Native Cargo still completes both selected
workloads substantially faster than the experimental custom engine.

All **168 commands** completed: 126 primary commands and 42 independent checking
controls. This includes 30 edited custom pairs, 18 expected wrong-edit failures,
six initial primary commands and twelve source-reverting primary anchors.
Original assertions/test sources were preserved. All 84 executed custom artifacts
were hash-verified and matched within each pair. All five project source pins
were rechecked and their tracked files were restored. No samples were discarded.

Native uses root O0/incremental, 18 Cargo jobs and default libtest concurrency;
custom modes use four jobs and the frozen workload-specific MIR/inlining/runtime
options. Package overrides remain. The instruction and allocation budgets are
unchanged, including the token allocation allowance of 150,000. This is not a
fastest-native comparison. Toolchain/dependency/std-MIR setup is excluded; OS
caches were not cleared and unrelated host work was not controlled.

Both fre workflows again produce different artifact bytes across source histories.
Pairwise identity holds, but cross-history semantic equivalence and the cause
of those layout differences remain unresolved. All histories and artifacts remain
in the individual reports.

The execution smoke recorded 11.53 million host tree entries versus 2.62 million
nested generated Calls for folded; token had 32.27 million host entries versus
57.18 million nested Calls. These counts show the remaining VM boundary, not a
causal decomposition or a prediction of further speedup. The next implementation
will link eligible direct Call stubs with ordinary JIT regions while preserving
whole-call readiness/budgets, guest live bounds, exact copies, fault exits and
profile accounting. It must meet the same gates against b2aa6efe.

The candidate passes 225 workspace tests in debug and release (one ignored),
seven CLI checks and both saved real-artifact smoke checks. The seven held-out
workflows and broader native/TLS/fre execution suites were not run on this
candidate because the primary gates failed. They remain required before retention.

[Gate calculations](gate-evaluation.json) · [Final verification](final-verification.json) ·
[Folded raw summary](../bounded-native-e2e-01-folded-literal-trie/summary.json) ·
[Token raw summary](../bounded-native-e2e-01-token-phrase/summary.json) ·
[Next implementation](../../benchmarks/experiments/bounded-native-calls/REGION-CALLS-NEXT.md)
