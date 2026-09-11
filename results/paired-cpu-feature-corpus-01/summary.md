# CPU-query candidate: eleven production-edit workflows

All 55 old/new JIT comparisons pass the original selected tests, reject a wrong production edit and execute identical bytecode within each pair. The five source pins were checked after all runs and are restored. The new CPU-query capability is still unselected: this corpus does not establish a performance improvement.

| Workflow | Native median (s) | Prior JIT (s) | Candidate JIT (s) | Paired command change (ms) | Paired execution change (ms) | Wins |
|---|---:|---:|---:|---:|---:|---:|
| [fre-word64](../e2e-paired-fre-word64-cpu-feature-01/summary.md) | 1.637 | 2.300 | 2.251 | -44.503 | -1.252 | 4/5 |
| [fre-word64-inline8](../e2e-paired-fre-word64-inline8-cpu-feature-01/summary.md) | 1.742 | 1.794 | 1.854 | +74.857 | +7.089 | 1/5 |
| [pgrust-sha1-inline8](../e2e-paired-pgrust-sha1-inline8-cpu-feature-01/summary.md) | 0.738 | 0.966 | 0.949 | -11.811 | +1.609 | 4/5 |
| [pgrust](../e2e-paired-pgrust-cpu-feature-broad-01/summary.md) | 0.678 | 0.525 | 0.542 | +12.549 | +0.042 | 1/5 |
| [fre-class-sequence](../e2e-paired-fre-class-sequence-cpu-feature-broad-01/summary.md) | 1.618 | 0.899 | 0.957 | +57.407 | -0.177 | 1/5 |
| [nushell](../e2e-paired-nushell-cpu-feature-broad-01/summary.md) | 0.660 | 0.451 | 0.439 | +5.029 | +0.078 | 2/5 |
| [ruff](../e2e-paired-ruff-cpu-feature-broad-01/summary.md) | 5.571 | 2.715 | 2.753 | +136.387 | +0.209 | 1/5 |
| [rg-aot](../e2e-paired-rg-aot-cpu-feature-broad-01/summary.md) | 0.541 | 0.194 | 0.198 | +3.845 | +0.062 | 2/5 |
| [nushell-type-relations](../e2e-paired-nushell-type-relations-cpu-feature-broad-01/summary.md) | 10.180 | 5.210 | 6.163 | +978.564 | +0.592 | 1/5 |
| [fre-grapheme-scalar-dfa](../e2e-paired-fre-grapheme-scalar-dfa-cpu-feature-broad-01/summary.md) | 1.329 | 0.804 | 0.839 | +16.148 | -0.037 | 1/5 |
| [fre-packed-literal-set](../e2e-paired-fre-packed-literal-set-cpu-feature-broad-01/summary.md) | 1.430 | 0.871 | 0.872 | -5.123 | -0.210 | 3/5 |

The candidate wins 21/55 complete-command pairs. The large Nushell type-relation workflow loses four of five, with a +0.979 s median paired command change. Its guest execution changes by only +0.592 ms. About 854 ms of the median paired difference in Cargo is outside the selected test target's frontend/export timers. Additional Cargo unit timing diagnostics are required before attributing that gap or selecting a default build.

A [completed diagnostic repeat](../cpu-feature-nushell-diagnostic-01/summary.md) adds a separate five-pair observation: two candidate wins and a +434 ms median paired change. Cargo reports locate most variation before the selected test unit; the cause remains unresolved. The initial 55-pair corpus above is unchanged.

Every sample is retained; five shared-host pairs are not confidence intervals. Differences between separate medians need not equal a median paired difference. Timings include actual production edits and test execution. Cold measurements exclude tool bootstrap, downloads and reusable standard-library MIR setup; exact flags, cold observations and raw records are linked per workflow. Private rg-aot details remain in the private raw workflow, with aggregate timings here.

[New coverage and full correctness gates](../cpu-feature-capability-01/summary.md), [complete folded-trie workflow, which remains slower than native](../e2e-workflow-fre-folded-literal-trie-cpu-feature-01/summary.md), [same-artifact runtime screen](../cpu-feature-runtime-01/summary.md).
