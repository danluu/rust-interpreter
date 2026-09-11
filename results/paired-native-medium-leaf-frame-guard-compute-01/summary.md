# Medium aggregate leaf inlining with frame limit: four production-edit workflows

The candidate wins **13/20** complete edited-command pairs against the prior custom JIT. Native wins 17/20 comparisons against the candidate. All selected original tests pass, all modes reject the deliberately wrong edit, and both source checkouts are restored.

| Workflow | Native median (s) | Prior JIT (s) | Candidate JIT (s) | Paired command change (ms) | Paired execution change (ms) | Wins |
|---|---:|---:|---:|---:|---:|---:|
| [fre-folded-literal-trie](../e2e-paired-fre-folded-literal-trie-native-medium-leaf-frame-guard-01/summary.md) | 1.675 | 3.560 | 3.531 | -25.403 | -32.861 | 4/5 |
| [fre-word64](../e2e-paired-fre-word64-native-medium-leaf-frame-guard-01/summary.md) | 1.846 | 2.325 | 2.292 | -35.943 | -23.206 | 3/5 |
| [fre-word64-inline8](../e2e-paired-fre-word64-inline8-native-medium-leaf-frame-guard-01/summary.md) | 1.719 | 1.721 | 1.717 | -9.203 | -3.290 | 3/5 |
| [pgrust-sha1-inline8](../e2e-paired-pgrust-sha1-inline8-native-medium-leaf-frame-guard-01/summary.md) | 0.734 | 0.934 | 0.929 | -2.559 | -2.289 | 3/5 |

The opt-in leaf inliner accepts fixed body, argument and result copies up to 128 bytes, requiring new aggregate leaves to add at most half the original caller frame including alignment. Existing small-copy eligibility and other growth limits remain. Both builds use identical VM binaries, strict frontend checking, guest MIR options and leaf-inlining settings. Every pair records whether its bytecode changes. Timing differences for identical bytecode on the identical VM do not demonstrate an execution-code improvement. Command times include Cargo, checking, export, launch, JIT construction and original-test execution.

Every timing, mode order, source edit, artifact hash and cold/setup cost is retained in the linked reports. Five pairs per workflow on a shared host do not establish confidence intervals. Separate stage medians need not add to the command median. The full eighteen-test folded-trie suite is included; these selected tests are not complete application support.

[Runtime screen](../native-medium-leaf-frame-guard-real-screen-01/summary.md), [broad native correctness](../native-medium-leaf-frame-guard-default-validation-01.json).

The three fre workflows change all fifteen artifact pairs and win ten full commands. SHA-1 keeps all five artifact pairs identical and wins three; those differences do not show an execution-code gain. Folded-trie improves all five execution stages. This modest result advances to fresh original-test coverage and the broader corpus; qualification remains pending.
