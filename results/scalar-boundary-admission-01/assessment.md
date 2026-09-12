# Scalar boundary address admission

The unchanged scalar transform admits 453 of 526 folded and 1,542 of 1,813 token MIR-eligible boundary slots. All eleven tests pass, including the eight existing scalar-transform/move tests. Both original profiles reconcile again; probe bodies are discarded and never execute.

| Workload | Admitted argument copies | Admitted scalar returns | Probe operations |
| --- | ---: | ---: | ---: |
| folded-literal-trie | 20,337,817 | 761,556 | 108,119 |
| token-phrase | 85,796,778 | 47,664,110 | 352,757 |

No analysis reached the 32-million-operation bound. The static proof includes cold code, exact widths, register definitions and block-local dominance. Almost all dynamically observed full scalar accesses remain in the admitted subset. Rejected rows remain recorded; token excludes 2,746,789 candidate argument copies and 1,734 scalar returns.

Admission proves address shape only. It does not prove argument initialization, result publication or caller value compatibility. The next [versioned ABI contract](../../benchmarks/experiments/scalar-value-abi/CONTRACT.md) keeps legacy Program bytes and uses separate scalar metadata. Counts are not a latency forecast.

The [summary](summary.json) binds every original artifact/profile, source and output; [execution](execution.json) records the terminal process chain.
