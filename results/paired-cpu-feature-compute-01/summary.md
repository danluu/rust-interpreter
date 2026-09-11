# CPU-query candidate: existing compute workflows

Five cumulative production edits per workflow, unchanged original tests, an effective wrong-edit control in every mode and identical bytecode within every old/new JIT pair. Both custom builds use explicit MIR3 and leaf inlining; inline8 additionally raises MIR inlining thresholds. Native retains its development/test profile.

| Workflow | Native median (s) | Prior JIT (s) | Candidate JIT (s) | Paired command change (ms) | Paired Cargo change (ms) | Paired execution change (ms) | Wins |
|---|---:|---:|---:|---:|---:|---:|---:|
| [fre-word64](../e2e-paired-fre-word64-cpu-feature-01/summary.md) | 1.637 | 2.300 | 2.251 | -44.503 | -36.490 | -1.252 | 4/5 |
| [fre-word64-inline8](../e2e-paired-fre-word64-inline8-cpu-feature-01/summary.md) | 1.742 | 1.794 | 1.854 | +74.857 | +75.409 | +7.089 | 1/5 |
| [pgrust-sha1-inline8](../e2e-paired-pgrust-sha1-inline8-cpu-feature-01/summary.md) | 0.738 | 0.966 | 0.949 | -11.811 | -18.948 | +1.609 | 4/5 |

The candidate wins 9/15 complete commands. Most of the observed command differences are in Cargo. Execution-stage median paired changes range from −1.3 to +7.1 ms. These five shared-host pairs per workload establish successful edited commands, not confidence intervals or an overall speedup. Cold commands, all samples, exact artifacts, load observations and source provenance remain in each linked report.

The separate new folded-trie workflow is slower than native. Broader project qualification remains in progress. [New coverage and its limitations](../cpu-feature-capability-01/summary.md), [same-artifact runtime screen](../cpu-feature-runtime-01/summary.md).
