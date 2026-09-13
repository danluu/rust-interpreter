# Memory and compiler-lookup composition clears all five gates

All 726 commands have their expected outcomes across Nushell, private rg-aot, token, folded and pgrust. All five predeclared engineering gates pass. The source integration and complete-tool verification are next; runtime source has not yet been imported into main.

| Case | Wall change versus wide | CPU change versus wide | Wall / CPU A/A | Candidate / ordinary native wall | Gate |
| --- | ---: | ---: | ---: | ---: | --- |
| nushell | -0.93% | -0.60% | 5.73% / 2.23% | 0.629 | pass |
| rg-aot | -12.55% | -11.53% | 2.46% / 1.61% | 0.396 | pass |
| token | -7.66% | -6.78% | 5.25% / 3.94% | 1.894 | pass |
| folded | -1.46% | -0.98% | 2.12% / 2.11% | 0.932 | pass |
| pgrust | -5.47% | -4.73% | 1.55% / 1.58% | 0.890 | pass |

The twelve-test token primary improves 18.35% wall and 17.88% CPU against the fixed selected-suite anchor. It still takes 1.894 times ordinary native Cargo. The candidate combines the qualified custom memory-operand VM with cached compiler-identity discovery; exporter and wrapper bytes match the wide control. This comparison measures that combination, not independent component effects.

Nushell and folded changes are inside their observed A/A envelopes: their guards pass, but they establish no useful incremental speedup. The private and pgrust commands show larger effects from the composition. Strict rustc type and borrow checks still run before execution; the lookup cache skips identity discovery only.

Every case retains three cycles, fifteen valid edited pairs, fifteen A/A pairs, original assertions, deliberate wrong edits and compiled restoration. Ratios are medians of per-edit ratios; do not divide independently calculated stage or command medians to reproduce them. All modes use two Cargo workers; ordinary native retains default libtest concurrency. Initial empty-target observations and unchanged builds do not establish a latency gain.

Final verification under the shared lock confirms all 8,996 unique case inputs and 440 harness inputs unchanged, all five sources restored, each supervisor terminal with exit zero, and every report complete with matching evidence hashes. Private source, names and raw commands remain local. No completed case was retimed and no pairs were omitted.

Keep the earlier memory-only and lookup-only failed decisions unchanged. Their components were tested together under this new protocol. A/A margins are descriptive engineering rules, not confidence intervals or statistical upper bounds.

Next import the exact qualified Rust and launcher sources from a branch based on current main, build all tools, identify the new binaries and qualify actual exports before merging. Keep the drafted binding-cost observer separate. Current token lowering includes about 124 ms of rebinding inside 612 ms total lowering, while the VM stage remains about 3.077 s; these measured costs guide subsequent work.
