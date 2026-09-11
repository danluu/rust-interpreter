# Medium aggregate leaf inlining with a frame-growth guard: twelve workflows

The candidate wins **35/60** complete production-edit command pairs against the prior JIT. Native wins 17/60 comparisons against the candidate. Every selected original test passes, every mode rejects each deliberately wrong production edit, and all five source pins are restored.

| Workflow | Native median (s) | Prior JIT (s) | Candidate JIT (s) | Paired command change (ms) | Paired execution change (ms) | Wins | Identical bytecode |
|---|---:|---:|---:|---:|---:|---:|---:|
| [fre-folded-literal-trie](../e2e-paired-fre-folded-literal-trie-native-medium-leaf-frame-guard-01/summary.md) | 1.675 | 3.560 | 3.531 | -25.403 | -32.861 | 4/5 | 0/5 |
| [fre-word64](../e2e-paired-fre-word64-native-medium-leaf-frame-guard-01/summary.md) | 1.846 | 2.325 | 2.292 | -35.943 | -23.206 | 3/5 | 0/5 |
| [fre-word64-inline8](../e2e-paired-fre-word64-inline8-native-medium-leaf-frame-guard-01/summary.md) | 1.719 | 1.721 | 1.717 | -9.203 | -3.290 | 3/5 | 0/5 |
| [pgrust-sha1-inline8](../e2e-paired-pgrust-sha1-inline8-native-medium-leaf-frame-guard-01/summary.md) | 0.734 | 0.934 | 0.929 | -2.559 | -2.289 | 3/5 | 5/5 |
| [pgrust](../e2e-paired-pgrust-native-medium-leaf-frame-guard-broad-01/summary.md) | 0.671 | 0.520 | 0.515 | -5.632 | +0.238 | 3/5 | 0/5 |
| [fre-class-sequence](../e2e-paired-fre-class-sequence-native-medium-leaf-frame-guard-broad-01/summary.md) | 1.371 | 0.786 | 0.763 | -18.322 | -0.022 | 5/5 | 0/5 |
| [nushell](../e2e-paired-nushell-native-medium-leaf-frame-guard-broad-01/summary.md) | 0.677 | 0.467 | 0.460 | +11.925 | +0.088 | 1/5 | 5/5 |
| [ruff](../e2e-paired-ruff-native-medium-leaf-frame-guard-broad-01/summary.md) | 5.940 | 3.376 | 3.521 | +145.199 | -0.474 | 2/5 | 3/5 |
| [rg-aot](../e2e-paired-rg-aot-native-medium-leaf-frame-guard-broad-01/summary.md) | 0.534 | 0.203 | 0.206 | +0.498 | -0.127 | 2/5 | 0/5 |
| [nushell-type-relations](../e2e-paired-nushell-type-relations-native-medium-leaf-frame-guard-broad-01/summary.md) | 14.485 | 7.596 | 7.258 | +555.666 | +0.201 | 2/5 | 0/5 |
| [fre-grapheme-scalar-dfa](../e2e-paired-fre-grapheme-scalar-dfa-native-medium-leaf-frame-guard-broad-01/summary.md) | 1.675 | 0.952 | 0.962 | -20.412 | +0.257 | 3/5 | 0/5 |
| [fre-packed-literal-set](../e2e-paired-fre-packed-literal-set-native-medium-leaf-frame-guard-broad-01/summary.md) | 1.489 | 0.916 | 0.906 | -13.343 | +0.384 | 4/5 | 0/5 |

Changed-bytecode cases win 30/47 pairs; identical-bytecode cases win 5/13. Timing differences for identical bytecode on the identical VM do not demonstrate execution-code gains, but their complete commands still measure compiler and launcher costs.

The opt-in leaf inliner accepts fixed body, argument and result copies through 128 bytes. Newly eligible aggregate leaves may add at most half the original caller frame, including alignment padding. Existing small-copy eligibility, the 512-byte callee-frame bound, and the other code-growth and correctness guards remain. Selection uses no function-name rules or runtime profile.

Both builds use the identical VM, strict frontend checking, matching guest MIR flags and matching leaf-inlining settings. Command timings include Cargo, checking, export, launch, JIT construction and original-test execution. All artifact-pair identity flags were checked against retained file hashes. The original eighteen-test folded-trie suite is included.

Fresh native controls preserve all 303 passing fre tests and all 389 classifications: 62 lowering-blocked, 7 ignored and 17 runtime-unsupported cases remain. These are selected library-test workflows, not whole-application support. Five pairs per workflow on a shared host do not establish confidence intervals; stage medians need not add to the command median.

Every sample, edit, mode order, cold/setup cost and artifact hash is retained in the linked reports. Downloads, tool bootstrap and standard-library MIR setup are outside command timings. The historical qualified reference remains distinct from the current working tree.

[Fresh coverage](../audit-execution-fre-native-medium-leaf-frame-guard-01/summary.md), [native correctness](../native-medium-leaf-frame-guard-default-validation-01.json), [runtime screen](../native-medium-leaf-frame-guard-real-screen-01/summary.md), [unguarded experiment](../paired-native-medium-leaf-compute-01/summary.md).
