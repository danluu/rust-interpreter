# Native medium copies: four production-edit workflows

The candidate wins **17/20** complete-command pairs against the previous custom JIT. All original tests pass, every mode rejects the wrong production edit, and every paired export is byte-for-byte identical. Native wins 20/20 comparisons against the candidate. The complete eighteen-test folded-trie suite remains included.

| Workflow | Native median (s) | Prior JIT (s) | Candidate JIT (s) | Paired command change (ms) | Paired execution change (ms) | Candidate wins |
|---|---:|---:|---:|---:|---:|---:|
| [fre-folded-literal-trie](../e2e-paired-fre-folded-literal-trie-native-medium-copy-01/summary.md) | 1.770 | 3.796 | 3.647 | -203.406 | -147.128 | 5/5 |
| [fre-word64](../e2e-paired-fre-word64-native-medium-copy-01/summary.md) | 1.878 | 2.402 | 2.344 | -58.623 | -46.154 | 5/5 |
| [fre-word64-inline8](../e2e-paired-fre-word64-inline8-native-medium-copy-01/summary.md) | 1.697 | 1.788 | 1.740 | -48.634 | -36.706 | 5/5 |
| [pgrust-sha1-inline8](../e2e-paired-pgrust-sha1-inline8-native-medium-copy-01/summary.md) | 0.782 | 0.955 | 0.951 | +3.652 | +1.082 | 2/5 |

The change emits native copies through 128 bytes. Every comparison uses the same leaf-inlining and guest MIR settings in both JIT builds. Command times include Cargo, strict checking, bytecode export, launch, JIT construction and original-test execution. The separate stage medians need not add to the complete-command median. All samples and exact mode orders remain in the linked reports.

Cold commands, tool identities, artifact hashes and setup exclusions are retained per workflow. These are source-edit measurements on a shared host, not unchanged-build measurements or confidence intervals. Broad native correctness checks pass, but the larger-project corpus and fresh original-test coverage replay remain before selection. The CPU-query baseline remains experimental, and the previously selected build remains recorded.

[Runtime screen, including the SHA-1 regression without leaf inlining](../native-medium-copy-runtime-01/summary.md), [broad correctness record](../native-medium-copy-default-validation-01.json).
