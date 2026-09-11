# Scratch-frame reuse: four production-edit workflows

The candidate wins **10/20** complete edited-command pairs against the prior custom JIT. Native wins 18/20 comparisons against the candidate. All selected original tests pass, all modes reject the deliberately wrong edit, and both source checkouts are restored.

| Workflow | Native median (s) | Prior JIT (s) | Candidate JIT (s) | Paired command change (ms) | Paired execution change (ms) | Wins |
|---|---:|---:|---:|---:|---:|---:|
| [fre-folded-literal-trie](../e2e-paired-fre-folded-literal-trie-temporary-frame-01/summary.md) | 2.109 | 3.762 | 3.712 | +3.129 | -53.823 | 2/5 |
| [fre-word64](../e2e-paired-fre-word64-temporary-frame-01/summary.md) | 1.673 | 2.322 | 2.274 | -58.335 | -5.644 | 4/5 |
| [fre-word64-inline8](../e2e-paired-fre-word64-inline8-temporary-frame-01/summary.md) | 1.803 | 1.759 | 1.837 | +61.252 | -4.806 | 0/5 |
| [pgrust-sha1-inline8](../e2e-paired-pgrust-sha1-inline8-temporary-frame-01/summary.md) | 0.748 | 0.955 | 0.938 | -18.803 | -2.034 | 4/5 |

The exporter reuses fully initialized compiler scratch slots between MIR operations while preserving permanent locals. Both builds use identical VM binaries, strict frontend checking, guest MIR options and leaf-inlining settings. Exported bytecode changes because temporary offsets and frame sizes change. Command times include Cargo, checking, export, launch, JIT construction and original-test execution.

Every timing, mode order, source edit, artifact hash and cold/setup cost is retained in the linked reports. Five pairs per workflow on a shared host do not establish confidence intervals. Separate stage medians need not add to the command median. The full eighteen-test folded-trie suite is included; these selected tests are not complete application support.

[Runtime screen](../temporary-frame-real-screen-01/summary.md), [broad native correctness](../temporary-frame-default-validation-01.json).

The change is **not retained**. Its small runtime gains did not produce consistent complete-command gains, and the inlined word64 workflow lost all five pairs. Most of that regression was in Cargo; the result does not establish that the scratch allocator caused the variation. The prior copy-emitter source and both binaries were explicitly rebuilt and verified against their retained hashes. The experiment and all results remain archived. A fresh 389-body survey and the broader project corpus were deliberately skipped after this compute gate.
