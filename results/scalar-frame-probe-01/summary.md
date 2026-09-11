# Isolated scalar frame reuse: promising compute result, compiler overhead remains

The retained engine remains **cd347**. The isolated **4cca** candidate wins **5/10** complete production-edit commands across two fre workflows. Folded trie improves; the TLS workflow regresses. Native still wins every folded-trie pair.

The rustc frontend remains strict. The custom exporter colors only primitive scalar locals whose uses prove they can share storage. Arguments, return values, aggregates, projected or borrowed locals, call destinations, and values that may read their entry zeroes stay dedicated. The pass includes all MIR edges, dead writes and same-statement interference, keeps a work bound, and preserves full frame initialization. The VM binary is identical.

The observation-only exporter captured 1,045 distinct instances and reproduced the retained artifact exactly. Storage markers survived in 407 functions but were absent from the seven largest contributors to direct-call frame volume. MIR locals account for 91% of that volume. An initial diagnostic keyed by display name collided for two unused instances; the corrected run uses function IDs, and the first run is retained with that limitation.

The actual scalar prototype reduces declared direct-callee frame volume from **46.219 GB to 42.539 GB** over the same 26,495,637 direct calls. All 4,428,759,008 logical instruction counts, per-function counts and register counts match. Bytecode differences are local offsets and 292 smaller inline-bank fill sizes; those 292 sites are unexecuted in this profile. The byte-volume figure excludes alignment padding, indirect calls and runtime TLS callbacks and is not a CPU-time measurement.

Three focused allocator tests and 18 fresh native controls pass. The six balanced same-VM execution pairs all improve, saving a median paired **34.580 ms**. This is a direction screen, separate from the complete edited commands below.

| Workflow | Command wins | Native wins | Paired command change | Paired execution change | Paired Cargo change | New pass median |
|---|---:|---:|---:|---:|---:|---:|
| folded-literal-trie | 4/5 | 0/5 | -42.619 ms | -87.965 ms | +29.025 ms | 25.481 ms |
| forward-anchored-tls | 1/5 | 5/5 | +7.975 ms | +0.490 ms | +9.814 ms | 15.067 ms |

Negative changes favor the candidate. Stage medians need not add to the command median. All original tests are unchanged, all wrong production edits are rejected, both seven-artifact comparisons change, and every baseline artifact matches its retained predecessor. The owned fre source is restored. Raw pairs, cold commands, source/artifact identities and timings remain in the linked reports.

Next reduce the 15–25 ms analysis cost without changing layouts: use a bounded dense liveness/interference representation, preserve deterministic coloring and fallback decisions, and require exact old/new plan and bytecode matches before repeating the edited commands. The allocation-heavy version remains isolated. Larger projects, broad runtime differentials and fresh 389-body coverage are still required before retaining a new engine. The matched-MIR native control and allocation-count limit remain separate outstanding work.

[Folded-trie full commands](../paired-scalar-frame-folded-literal-trie-01/summary.md), [TLS full commands](../paired-scalar-frame-forward-anchored-tls-01/summary.md).
