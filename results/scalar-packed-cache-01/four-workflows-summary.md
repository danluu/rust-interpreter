The isolated custom JIT combines restricted MIR scalar promotion and its entry-register initialization proof with the retained native register cache. Strict checking and original test assertions are preserved.

Across 4 source-edit workflows it wins **16/20 complete commands** against the retained build and **8/20 against native Cargo**. Execution alone improves in 18/20 pairs. The candidate remains isolated pending a retention decision. These selected library tests do not establish whole-application support or a broad warm-compilation improvement.

| Workflow | Parent wins | Paired command change | Execution change | Cargo change | Native wins |
|---|---:|---:|---:|---:|---:|
| token-phrase | 4/5 | -175.0 ms | -159.3 ms | +29.5 ms | 0/5 |
| folded-literal-trie | 3/5 | -78.1 ms | -39.9 ms | -102.7 ms | 0/5 |
| forward-anchored-tls | 4/5 | -98.2 ms | -37.5 ms | -51.4 ms | 5/5 |
| pgrust-sha1-inline8 | 5/5 | -46.9 ms | -23.9 ms | -19.7 ms | 3/5 |

All samples are retained, including regressions. Paired medians use within-edit differences; marginal medians below are separate statistics. Stage medians need not sum to the command median.

| Workflow | Median native / retained / candidate | Cold native / retained / candidate |
|---|---|---|
| token-phrase | 2.279 / 7.098 / 6.917 s | 7.668 / 11.848 / 11.840 s |
| folded-literal-trie | 2.324 / 3.076 / 2.961 s | 7.764 / 7.835 / 8.666 s |
| forward-anchored-tls | 1.910 / 1.574 / 1.341 s | 7.166 / 6.515 / 7.113 s |
| pgrust-sha1-inline8 | 0.817 / 0.877 / 0.766 s | 1.175 / 1.217 / 0.881 s |

All 172 bytecode tests, 11 exporter tests, 47,004 fresh native differential commands and 245 TLS/callback checks pass. Full fresh fre qualification selects 389 tests: 382 pass, seven remain ignored, and all active tests pass against fresh native executions. No passing test declines native compilation. The explicit allocation limit for that suite is 150,000; the default remains 100,000. Actual unwinding and general OS/FFI execution remain unsupported.

The exporter binary differs from scalar81 even though its source is identical. The original failed identity expectation is preserved. Every newly exported fre body and every candidate artifact in the edit workflows matches scalar81 exactly. Baseline artifacts match the retained history, each wrong edit is rejected, and project sources are restored.

A fresh source copy and clean target reproduce both measured binaries exactly.

The earlier eight-cycle four-way runtime filter won 7/8 against retained, saving paired medians of 47.5 ms elapsed and 46.9 ms CPU. Logical operations on the original folded-trie tests fall from 4,428,759,008 to 4,138,403,285. Same-artifact traces match; no cross-artifact PC-equivalence claim is made. The combined VM on the original bytecode alone regressed 4.8 ms. That filter uses historical artifacts, separately from the fresh edited commands above.

Earlier large-Nushell identical-tool controls show substantial unexplained variation. No control value is subtracted from these measurements, and no Cargo timing change is attributed to register allocation merely from these paired samples. Raw commands, source and tool hashes, artifacts, failed expectations and earlier reports remain available in the workspace.
