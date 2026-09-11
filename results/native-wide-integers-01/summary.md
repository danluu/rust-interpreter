# Native 128-bit subtraction and comparisons

Candidate `81967134638a29bfec7ef37ee8b1addf3819e712007acb31fd5991efe68e13c7` adds direct AArch64 emission for full-width subtraction and integer comparisons. The profile identified genuine 128-bit enum tags near `u128::MAX`, so narrowing would change semantics. Frontend checks and exported bytecode remain unchanged.

All 134 bytecode tests, 47,004 native differential commands, and 245 TLS checks pass. The tests include independent native Rust results, borrow propagation, signed overflow, register aliases, instruction budgets, fault order, and logical profiles.

Retained-program replay preserves **381 passing ordinary fre tests** against 382 fresh native executions. One retains the existing live-allocation-count error; seven are ignored. These are retained MIR programs, not a new frontend collection or whole-application guarantee.

The tuned folded-trie profiles match all **4,448,026,812 logical instructions**. Native entries fall from 53,069,320 to 50,802,123. Both folded-trie runtime screens win six of six pairs; TLS and the small control have sub-millisecond paired median regressions. These screens do not measure compilation.

| Production-edit workflow | Command wins vs parent | Paired command change | Paired execution change | Wins vs native |
|---|---:|---:|---:|---:|
| [folded-literal-trie](../paired-native-wide-folded-literal-trie-01/summary.md) | 4/5 | -94.8 ms | -53.6 ms | 0/5 |
| [forward-anchored-tls](../paired-native-wide-forward-anchored-tls-01/summary.md) | 2/5 | +3.4 ms | +1.2 ms | 5/5 |
| [nushell](../paired-native-wide-corpus-nushell-01/summary.md) | 4/5 | -19.4 ms | +0.1 ms | 5/5 |
| [nushell-type-relations](../paired-native-wide-corpus-nushell-type-relations-01/summary.md) | 2/5 | +302.1 ms | +0.2 ms | 5/5 |
| [pgrust](../paired-native-wide-corpus-pgrust-01/summary.md) | 1/5 | +2.3 ms | -0.2 ms | 5/5 |
| [pgrust-sha1-inline8](../paired-native-wide-corpus-pgrust-sha1-inline8-01/summary.md) | 2/5 | +5.2 ms | +1.2 ms | 0/5 |
| [rg-aot](../paired-native-wide-corpus-rg-aot-01/summary.md) | 3/5 | -0.6 ms | -0.0 ms | 5/5 |
| [ruff](../paired-native-wide-corpus-ruff-01/summary.md) | 2/5 | +108.5 ms | -0.0 ms | 5/5 |

All 8 workflows preserve 56 artifact pairs, reject every deliberately wrong production edit, and leave original tests unchanged. Folded-trie execution improves in every pair; the TLS result is effectively flat. Native still wins all five folded-trie comparisons. Paired changes compare the same source edit; separate medians of raw command times need not rank the variants in the same order.

The candidate wins 20/40 paired edited commands against its parent and 30/40 against native. Ruff regresses by a paired 108 ms and larger Nushell by 302 ms, primarily in Cargo; execution changes are below a millisecond and both exporter binaries are identical. These differences remain in the results and are not attributed to the emitter. Retain the candidate as a targeted runtime improvement; a broad warm-build gain is not established. MIR defaults, native-code capacity, strict type/borrow checking, and unsupported-call behavior remain unchanged.
