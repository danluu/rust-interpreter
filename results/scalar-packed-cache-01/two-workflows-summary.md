The isolated build combines restricted MIR scalar promotion and entry-register initialization proof with the retained native register cache. The source changes are disjoint. Strict rustc checking, original test assertions, runtime traps and resource limits remain in place.

It wins 7/10 full edited commands against the retained build and 0/10 against native Cargo. Every sample is retained. These two selected-test workflows do not establish whole-application support or a broad warm-compilation improvement.

| Workflow | Parent wins | Paired command change | Execution change | Cargo change | Native wins |
|---|---:|---:|---:|---:|---:|
| folded-literal-trie | 3/5 | -78.1 ms | -39.9 ms | -102.7 ms | 0/5 |
| token-phrase | 4/5 | -175.0 ms | -159.3 ms | +29.5 ms | 0/5 |

Paired medians use within-edit differences. Marginal medians below answer a different question. Stage medians need not sum to the command median.

| Workflow | Median native / retained / candidate | Cold native / retained / candidate |
|---|---|---|
| folded-literal-trie | 2.324 / 3.076 / 2.961 s | 7.764 / 7.835 / 8.666 s |
| token-phrase | 2.279 / 7.098 / 6.917 s | 7.668 / 11.848 / 11.840 s |

All 172 bytecode and 11 exporter tests pass. The initial binary-identity expectation failed and is preserved: exporter source matches scalar81, but the compiled binary differs in text and data. All fourteen freshly exported candidate artifacts in these workflows exactly match scalar81, and all fourteen baseline artifacts match the retained build. Each wrong edit is rejected and project sources are restored. Broader qualification remains pending.

The four-way runtime filter uses eight balanced cycles on the original 18 folded-trie tests. The combination wins 7/8 against retained, saving paired medians of 47.5 ms elapsed and 46.9 ms CPU. Promotion reduces logical operations from 4,428,759,008 to 4,138,403,285. Same-artifact trace pairs match completely; PCs differ between promoted and original artifacts. The combined VM on the original artifact alone regresses by a paired 4.8 ms, retained as part of the result. This filter reuses historical artifacts and is separate from the fresh edit measurements above.

Sources, immutable tools, logs, hashes and failed expectations are retained in the workspace. The candidate is not integrated.
