**Parked without integration:** only 4/10 edited commands improve, and both paired command medians regress. The retained engine remains 6bf10fda.

The isolated exporter gives referenced virtual registers consecutive numbers after existing inlining and control-flow optimization. It preserves a distinct identity for every referenced register, including unread outputs. All 177 bytecode and 11 exporter tests pass. The native emitter is unchanged; both host binaries differ.

| Real source-edit workflow | Parent wins | Command / execution / Cargo change | Added compaction pass | Native wins |
|---|---:|---|---:|---:|
| folded-literal-trie | 2/5 | +254.25 / +52.12 / +246.95 ms | 4.14 ms | 1/5 |
| token-phrase | 2/5 | +33.38 / -304.67 / +20.70 ms | 18.43 ms | 0/5 |

Changes are medians of paired differences; stage medians need not sum to the command median. All outliers remain in the reports. The pass is included in Cargo time.

| Workflow | Median native / parent / candidate command | Cold native / parent / candidate command |
|---|---|---|
| folded-literal-trie | 3.199 / 3.229 / 3.563 s | 7.841 / 7.408 / 8.314 s |
| token-phrase | 2.137 / 7.184 / 6.899 s | 8.304 / 12.068 / 11.553 s |

Every workflow uses fresh exports and native controls, original assertions, five production edits and a deliberately wrong edit. All seven candidate artifacts exactly equal the typed compaction of their corresponding baseline, and inverse mapping reproduces every original artifact byte. Baseline artifacts match retained history, and project sources are restored.

| Saved-artifact runtime filter | Full candidate wins | Paired elapsed / CPU change |
|---|---:|---|
| folded | 4/8 | -39.14 / -33.22 ms |
| token-phrase | 5/8 | -7.41 / -20.28 ms |

The four-way runtime filter is inconclusive and excludes export/build work. It includes both VMs with both artifacts; no control timing is subtracted. Folded logical execution counts are identical after normalizing register names. Token uses production RNG, so cross-process traces differ. The exact native-code reductions are 9,280 bytes for folded and 4,688 for token. Almost all predicted folded address-instruction savings come from one existing test function crossing an addressing threshold; this is not evidence of a general runtime benefit.

The candidate remains isolated. Broader native/TLS/fre qualification and independent binary reproduction were not run because the measured edit workflows do not justify retention. Selected library tests do not establish whole-application support.
