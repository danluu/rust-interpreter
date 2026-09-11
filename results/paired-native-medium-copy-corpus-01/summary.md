# Native medium copies: twelve production-edit workflows

The candidate wins **38/60** complete-command pairs against the previous custom JIT. All selected original tests pass, every mode rejects the wrong production edit, and every paired export is byte-for-byte identical. Native wins 20/60 comparisons against the candidate. The complete eighteen-test folded-trie suite remains included.

| Workflow | Native median (s) | Prior JIT (s) | Candidate JIT (s) | Paired command change (ms) | Paired execution change (ms) | Candidate wins |
|---|---:|---:|---:|---:|---:|---:|
| [fre-folded-literal-trie](../e2e-paired-fre-folded-literal-trie-native-medium-copy-01/summary.md) | 1.770 | 3.796 | 3.647 | -203.406 | -147.128 | 5/5 |
| [fre-word64](../e2e-paired-fre-word64-native-medium-copy-01/summary.md) | 1.878 | 2.402 | 2.344 | -58.623 | -46.154 | 5/5 |
| [fre-word64-inline8](../e2e-paired-fre-word64-inline8-native-medium-copy-01/summary.md) | 1.697 | 1.788 | 1.740 | -48.634 | -36.706 | 5/5 |
| [pgrust-sha1-inline8](../e2e-paired-pgrust-sha1-inline8-native-medium-copy-01/summary.md) | 0.782 | 0.955 | 0.951 | +3.652 | +1.082 | 2/5 |
| [pgrust](../e2e-paired-pgrust-native-medium-copy-broad-01/summary.md) | 0.675 | 0.534 | 0.551 | +13.821 | +0.030 | 2/5 |
| [fre-class-sequence](../e2e-paired-fre-class-sequence-native-medium-copy-broad-01/summary.md) | 1.482 | 0.839 | 0.829 | -3.081 | +0.018 | 3/5 |
| [nushell](../e2e-paired-nushell-native-medium-copy-broad-01/summary.md) | 0.640 | 0.455 | 0.454 | +5.869 | -0.065 | 2/5 |
| [ruff](../e2e-paired-ruff-native-medium-copy-broad-02/summary.md) | 5.730 | 2.990 | 2.931 | -11.837 | -0.048 | 4/5 |
| [rg-aot](../e2e-paired-rg-aot-native-medium-copy-broad-01/summary.md) | 0.540 | 0.194 | 0.204 | +6.233 | -0.040 | 2/5 |
| [nushell-type-relations](../e2e-paired-nushell-type-relations-native-medium-copy-broad-01/summary.md) | 9.577 | 6.268 | 6.376 | +658.668 | -0.091 | 2/5 |
| [fre-grapheme-scalar-dfa](../e2e-paired-fre-grapheme-scalar-dfa-native-medium-copy-broad-01/summary.md) | 1.799 | 0.961 | 0.956 | -4.698 | -0.088 | 4/5 |
| [fre-packed-literal-set](../e2e-paired-fre-packed-literal-set-native-medium-copy-broad-01/summary.md) | 1.501 | 0.917 | 0.932 | +0.919 | -0.636 | 2/5 |

The change emits native copies through 128 bytes. Every comparison uses the same leaf-inlining and guest MIR settings in both JIT builds. Command times include Cargo, strict checking, bytecode export, launch, JIT construction and original-test execution. The separate stage medians need not add to the complete-command median. All samples and exact mode orders remain in the linked reports.

Cold commands, tool identities, artifact hashes and setup exclusions are retained per workflow. These are source-edit measurements on a shared host, not unchanged-build measurements or confidence intervals. Broad native correctness checks pass. A fresh replay preserves all 303 passing original tests and all 389 prior status classifications. This corpus covers selected original tests across five projects, not complete applications. The first Ruff attempt was interrupted by SIGTERM during the native cold build; its evidence is retained separately from the successful fresh retry. The CPU-query baseline remains experimental, and the previously selected build remains recorded.

[Runtime screen, including the SHA-1 regression without leaf inlining](../native-medium-copy-runtime-01/summary.md), [broad correctness record](../native-medium-copy-default-validation-01.json).

Retain the copy implementation as the experimental baseline for the next change. The clear runtime gains are in folded-trie and word64; SHA-1 and frontend-heavy command timings remain mixed. Both exporters are identical, so the large Nushell Cargo difference does not establish a cost in the copy emitter. The launcher uses the current working tree unless an explicit immutable `--tool-key` is supplied. The recorded qualified reference remains `07d14b7319a258900c1501322e65f3e43cd0977334920c8044035b42bfed9c9f`; the measured copy build is `cd9af4b45682d513b3b2079791e1e23b202efe97e0c09ba83a1902d6c1a9a722`.
