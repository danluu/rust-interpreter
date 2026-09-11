# Recorded aggregate pass cost in actual edits

| Workflow | Capture + finalize | Paired Cargo delta | Paired execution delta | Paired command delta |
| --- | ---: | ---: | ---: | ---: |
| folded-literal-trie | 41.9 ms | +37.6 ms | -285.9 ms | -253.7 ms |
| token-phrase | 189.5 ms | +237.4 ms | -79.3 ms | +157.3 ms |

Timers cover capture/finalization, not all earlier span/origin recording. Paired Cargo/execution deltas also contain other pass effects and host noise. Component medians need not add to command medians. No causal speedup claim or gate change follows from this diagnostic.

All 30 source-edit pairs are reverified from the completed primary histories. No compilation, execution, source edit or timing rerun was performed.
