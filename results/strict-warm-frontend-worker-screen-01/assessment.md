# Compiler frontend workers mechanism screen

Candidate median: 3.980660 s; baseline: 3.961189 s; independent baseline duplicate: 3.967813 s. 0 of five edited candidate commands were below 0.500 s. This single-history screen does not qualify the final latency target or holdout generalization.

Median paired wall change: -0.123%; CPU change: +2.512%. Maximum absolute A/A wall deviation: 3.084%; CPU deviation: 3.617%. These deviations describe the observed comparisons; they are not confidence intervals.

| Edit | Baseline wall s | Candidate wall s | Duplicate wall s | Baseline CPU s | Candidate CPU s | Duplicate CPU s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| combine-equal-and-supertype-widening-arms | 3.986977 | 3.962714 | 4.109924 | 6.777533 | 6.944635 | 7.022646 |
| collect-oneof-from-explicit-iterator | 3.905809 | 4.031446 | 3.967813 | 7.261255 | 7.713711 | 7.383855 |
| return-unrelated-widening-pair-early | 3.961189 | 3.994689 | 3.953590 | 6.728529 | 7.150812 | 6.746591 |
| express-subtype-test-with-is-some-and | 4.039597 | 3.980660 | 4.130823 | 7.107283 | 7.205595 | 7.176839 |
| make-union-pair-iterator-explicit | 3.953585 | 3.948735 | 3.911919 | 6.877263 | 7.050051 | 6.675664 |

Wall time includes the entire launcher, Cargo, VM, all 14 original tests and receipt I/O. Waited-child CPU may exceed wall time because compilers run concurrently. Nested stages remain separate; nothing is subtracted from complete-command time.

| Arm | Empty-target wall s | CPU s | All nine commands wall s |
| --- | ---: | ---: | ---: |
| baseline | 59.293715 | 169.767157 | 92.584854 |
| candidate | 60.420942 | 187.732075 | 93.677828 |
| duplicate | 63.989413 | 186.002663 | 96.601176 |

The one cold observation per arm includes its empty project cache; installed tools and prepared std MIR are separate setup. One cold observation does not establish a repeatable cold-build gain or regression.

All 27 commands, nine source states, five first-seen valid edited hashes per arm, all 14 original tests, deliberate wrong-result failures, compiled recovery and final restoration were checked. Outputs, outcomes, bytecode and entry catalogs agree across arms for every state. Source edits, manifests, features, units, profiles and checking requirements were preserved.

same stock compiler/tool binaries/std; explicit frontend workers 1/2/1. Only explicit frontend worker counts change (1/2/1). Stock compiler, tool binaries, standard library, Cargo jobs, backend/linker policy and checking remain equal. The final public build identity and separate actual 30-command worker qualification were verified.

[summary.json](summary.json) retains every pair, command, setup identity and artifact hash. [evidence.json.gz](evidence.json.gz) contains exact raw records, receipts, suites, source states, compiler/Cargo/tool provenance and frozen harness snapshots. All archive member hashes were checked. Compiler/tool binaries and project caches are not included in this compact archive. Linked qualification bytecode is retained where required. No adoption decision or fresh-project result is implied by packaging this screen.
