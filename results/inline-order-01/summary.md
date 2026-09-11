# Forwarding before leaf inlining

Eight-workflow cohort complete.

Identity wrappers are bypassed before leaf expansion can hide them. The final forwarding pass remains.
The existing eligibility, frame, initialization and code-growth limits are unchanged.

All 138 bytecode tests, 47,004 native differential commands, compiler/launcher checks and 245 TLS checks pass.
Both actual tool binaries differ; the VM implementation source is unchanged.

The separate exact-program runtime probe wins 6/6 pairs (-65 ms paired median), with the retained parent VM.
That screen is separate from the production-edit measurements below.

Each workflow uses five real production edits and unchanged original tests; wrong edits must fail.
Changes below are medians of paired candidate-minus-parent differences. Negative values are faster.

| Workflow | Native / parent / candidate medians (s) | Command change (ms) | Execution change (ms) | Wins vs parent / native |
|---|---:|---:|---:|---:|
| [folded-literal-trie](../paired-inline-order-folded-literal-trie-01/summary.md) | 2.379 / 3.049 / 2.993 | -61.8 | -36.1 | 4/5 / 0/5 |
| [forward-anchored-tls](../paired-inline-order-forward-anchored-tls-01/summary.md) | 1.461 / 1.162 / 1.182 | -15.2 | -7.7 | 3/5 / 5/5 |
| [pgrust](../paired-inline-order-corpus-pgrust-01/summary.md) | 0.640 / 0.508 / 0.513 | +6.4 | -0.0 | 2/5 / 5/5 |
| [ruff](../paired-inline-order-corpus-ruff-01/summary.md) | 5.798 / 2.865 / 2.968 | -92.2 | +0.2 | 4/5 / 5/5 |
| [nushell](../paired-inline-order-corpus-nushell-01/summary.md) | 0.657 / 0.442 / 0.438 | -2.1 | -0.1 | 3/5 / 5/5 |
| [rg-aot](../paired-inline-order-corpus-rg-aot-01/summary.md) | 0.553 / 0.199 / 0.199 | -0.4 | -0.1 | 3/5 / 5/5 |
| [pgrust-sha1-inline8](../paired-inline-order-corpus-pgrust-sha1-inline8-01/summary.md) | 0.739 / 0.900 / 0.915 | +5.5 | +3.2 | 1/5 / 0/5 |
| [nushell-type-relations](../paired-inline-order-corpus-nushell-type-relations-01/summary.md) | 9.536 / 5.472 / 5.753 | +261.2 | +0.0 | 2/5 / 5/5 |

Fresh exports preserve all 381 fre passes, with 382 passing native controls. Seven tests are ignored.
The remaining test has exactly the parent allocation-capacity error; there are no classification changes.
Maximum generated native code is 10,093,328 bytes; all passing tests have zero declined functions.

The candidate wins 22/40 pairs against the parent and 30/40 against native Rust.
Folded trie improves 4/5 complete commands (-62 ms paired) and all 5 execution stages (-36 ms).
Larger Nushell regresses 261 ms paired, mostly in Cargo (+251 ms); execution is effectively flat.
Ruff saves 92 ms paired, also mostly in Cargo. Neither result alone isolates a compiler-pass effect.
SHA-1 regresses 6 ms with all 7 artifact pairs identical; both actual VM binaries differ.
Retain the ordering as an experimental runtime improvement. A broad warm-build gain is not established.
Native still wins all 10 folded-trie/SHA-1 comparisons.

All artifact hashes were rechecked, and every baseline artifact matches its preceding run with retained build 8196. Changed candidate bytecode is expected.
Native controls use the established Cargo configuration; they are not a search over all native compiler settings.
These are selected library-test workflows, not whole-application support or an unchanged-build benchmark.
