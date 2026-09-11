# Empty unit-call removal: four production-edit workflows

The candidate wins **11/20** complete edited-command pairs against the prior custom JIT. Native wins 14/20 comparisons against the candidate. All selected original tests pass, all modes reject the deliberately wrong edit, and both source checkouts are restored.

| Workflow | Native median (s) | Prior JIT (s) | Candidate JIT (s) | Paired command change (ms) | Paired execution change (ms) | Wins |
|---|---:|---:|---:|---:|---:|---:|
| [fre-folded-literal-trie](../e2e-paired-fre-folded-literal-trie-empty-unit-call-01/summary.md) | 2.228 | 3.844 | 3.846 | -2.305 | -26.169 | 3/5 |
| [fre-word64](../e2e-paired-fre-word64-empty-unit-call-01/summary.md) | 2.456 | 2.536 | 2.634 | +4.780 | -3.727 | 2/5 |
| [fre-word64-inline8](../e2e-paired-fre-word64-inline8-empty-unit-call-01/summary.md) | 2.028 | 1.936 | 1.937 | -12.490 | +0.527 | 3/5 |
| [pgrust-sha1-inline8](../e2e-paired-pgrust-sha1-inline8-empty-unit-call-01/summary.md) | 0.777 | 0.960 | 0.949 | -3.160 | -2.172 | 3/5 |

The compiler removes proved direct calls to exactly Return/unit-result bodies after existing opt-in leaf expansion. Argument evaluation, function identities and existing expansion choices remain. The pass adds no frame or register storage. Strict frontend checking, guest MIR options and leaf-inlining settings match between the tool builds.

Both VM and exporter binaries differ in this complete-command comparison; every mode uses its actual retained binaries. The separate crossed runtime screen runs both artifacts on both VMs to help assess execution changes. These edited-command results must not be described as an identical-VM comparison.

Every timing, mode order, source edit, artifact hash and cold/setup cost is retained in the linked reports. All artifact identity flags were rechecked against the retained files. Five pairs per workflow on a shared host do not establish confidence intervals. Separate stage medians need not add to the command median. No A/A median is subtracted and no outlier is discarded.

Commands include Cargo, strict checking, export, launch, JIT construction and original-test execution. Downloads, tool bootstrap and reusable standard-library MIR setup are outside the timers. The complete eighteen-test folded-trie suite is included; these selected workflows are not whole-application support. The fresh 389-case fre survey and broader project corpus remain separate qualification steps.

[Crossed runtime screen](../empty-unit-call-real-screen-01/summary.md), [broad native correctness](../empty-unit-call-default-validation-01.json), [identical-tool calibration](../identical-tools-aa-e2e-01/summary.md).

Decision: archive the candidate and restore the guarded baseline. Both rebuilt binary hashes match the retained baseline exactly. The modest complete-command results do not justify further qualification. Fresh 389-case coverage and the broader corpus were deliberately not run for this rejected candidate. [Decision record](decision.json).
