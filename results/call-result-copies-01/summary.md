# Two call-result copying alternatives

Both alternatives remain parked without integration. The caller-local version improves both long-running artifacts in all twelve runtime comparisons, but wins only5/10 complete production-edit commands and0/10 against native Cargo. The minimal zero-result-only version was measured in the runtime screen and was not taken through edited-command comparisons.

A three-second CPU sample of retained88c01c captured2,554 stacks. Frame setup, argument copying and result copying account for602 (23.6%), including135 result-copy stacks. Exact-binary disassembly and the live executable mapping support the categories. Sample shares do not predict speedups. [CPU evidence](../retained-token-cpu-sample-01/summary.md).

A typed observer of the exact bytecode and saved profiles finds21,235,213 zero-result calls in token-phrase and9,383,531 in folded-trie. Every observed nonzero call result has a provably caller-local destination:77,123,080 and17,114,619 respectively. This conservative proof uses Local definitions, complete extents, explicit register-writer invalidation and basic-block boundaries. It does not use observed pointer values.

Alternative A skips copying zero-sized ordinary results, retaining the callee work, frames and Return instruction. Alternative B also combines the existing argument analysis with a destination flag stored in the call frame. Certified nonzero returns use safe copy_within; other destinations retain the checked general copy path. Frame size stays48 bytes. The JIT emitter, guest instruction sequence, initialization, memory budgets, indirect signature checks and TLS behavior are preserved. Exporter binaries differ, so the edited runs verify exact bytecode.

A passes167 bytecode tests; B passes172. Additional checks cover zero-sized dangling destinations, nested calls, exact budgets, nonzero readonly and bounds failures, all register writers, control-flow joins, indirect signatures, aliases and complete aggregates. The complete folded logical trace is identical in all three engines. Token-phrase profiles vary slightly with actual host randomness; no controlled RNG-input comparison was run for these parked candidates.

| Same-artifact runtime | Zero vs retained | Local vs retained | Local vs zero |
|---|---:|---:|---:|
| token-phrase | -69.22 ms (5/6) | -90.99 ms (6/6) | -19.64 ms (4/6) |
| folded | -28.77 ms (4/6) | -44.83 ms (6/6) | -20.37 ms (5/6) |
| sha1 | -0.56 ms (4/6) | +0.03 ms (3/6) | +0.09 ms (3/6) |
| tls | -0.36 ms (5/6) | -1.31 ms (4/6) | -0.98 ms (4/6) |
| pgrust-interpreter | -0.94 ms (3/6) | -4.49 ms (4/6) | -1.67 ms (4/6) |

Each artifact has six balanced cycles, with every engine appearing twice in each execution position. Wall and child CPU times are retained. Local-vs-retained CPU savings are89/43ms for token-phrase/folded, close to91/45ms wall savings. SHA-1 is effectively flat; TLS and the interpreter workflow change only slightly. Both candidates modify the interpreter path as well as JIT execution. All outliers and regressions remain in the raw records.

| Actual production edits, local candidate | Native / retained / candidate median | Paired command change | Execution change | Retained / native wins |
|---|---:|---:|---:|---:|
| [token-phrase](../paired-call-results-local-token-phrase-01/summary.md) | 2.312 / 7.086 / 7.064 s | -49.1 ms | -75.1 ms | 3/5 / 0/5 |
| [folded-literal-trie](../paired-call-results-local-folded-literal-trie-01/summary.md) | 1.893 / 2.826 / 2.877 s | +14.1 ms | +4.2 ms | 2/5 / 0/5 |

Both workflows preserve original tests, reject a wrong production edit under all three engines, and verify all seven exported states against retained bytecode. Token-phrase cold commands take8.036/12.051/12.318s for native/retained/candidate; folded takes7.490/7.618/7.549s. Cold regressions and Cargo variation remain visible.

Park both alternatives. The caller-local version saves a paired49ms per edited token-phrase command, including75ms in execution, but folded-trie regresses14ms per command and4ms in execution. These five wins in ten commands do not confirm the consistent same-artifact runtime improvement. Native wins all ten comparisons. This is a prioritization decision, not a correctness rejection or proof that the minimal alternative cannot help. Keep both implementations and all evidence; measure a larger MIR scalar-promotion opportunity next. Root remains88c01c.

Broader native differential, TLS and full fre replay drivers were prepared but not run for these candidates. Source, binaries and complete evidence are retained. No general warm-build gain or whole-application support is established.
