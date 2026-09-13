# Host-library code generation mechanism screen

Candidate median: 3.907370 s; baseline: 4.008823 s; independent baseline duplicate: 3.985424 s. 0 of five edited candidate commands were below 0.500 s. This single-history screen does not qualify the final latency target or holdout generalization.

Median paired wall change: -2.416%; CPU change: +0.557%. Maximum absolute A/A wall deviation: 2.219%; CPU deviation: 4.038%. These deviations describe the observed comparisons; they are not confidence intervals.

| Edit | Baseline wall s | Candidate wall s | Duplicate wall s | Baseline CPU s | Candidate CPU s | Duplicate CPU s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| combine-equal-and-supertype-widening-arms | 4.008823 | 3.982568 | 3.985424 | 6.808934 | 7.092342 | 6.763346 |
| collect-oneof-from-explicit-iterator | 4.004118 | 3.907370 | 3.948079 | 7.372069 | 6.731139 | 7.309339 |
| return-unrelated-widening-pair-early | 4.042490 | 4.009304 | 4.132174 | 6.848803 | 7.130429 | 7.125375 |
| express-subtype-test-with-is-some-and | 4.107829 | 3.827371 | 4.133199 | 7.280578 | 6.597409 | 7.126055 |
| make-union-pair-iterator-explicit | 3.986421 | 3.836404 | 3.984868 | 6.827282 | 6.865312 | 6.852967 |

Wall time includes the entire launcher, Cargo, VM, all 14 original tests and receipt I/O. Waited-child CPU may exceed wall time because compilers run concurrently. Nested stages remain separate; nothing is subtracted from complete-command time.

| Arm | Empty-target wall s | CPU s | All nine commands wall s |
| --- | ---: | ---: | ---: |
| baseline | 62.350127 | 175.666052 | 96.018470 |
| candidate | 80.628030 | 267.133753 | 113.132522 |
| duplicate | 61.640450 | 179.073551 | 94.592981 |

The one cold observation per arm includes its empty project cache; installed tools and prepared std MIR are separate setup. One cold observation does not establish a repeatable cold-build gain or regression.

All 27 commands, nine source states, five first-seen valid edited hashes per arm, all 14 original tests, deliberate wrong-result failures, compiled recovery and final restoration were checked. Outputs, outcomes, bytecode and entry catalogs agree across arms for every state. Source edits, manifests, features, units, profiles and checking requirements were preserved.

same public compiler/Cargo/exporter/VM/std; host-library codegen off/on/off. The compiler, Cargo, exporter, VM and prepared standard library are identical for off/on/off. Only eligible ordinary native host libraries receive O1 with original effective checks preserved. Actual three-history qualification, wrapper/compiler association and all saved input guards were verified. Application profiles, guest/build-script executable arguments and build-script environment are unchanged.

[summary.json](summary.json) retains every pair, command, setup identity and artifact hash. [evidence.json.gz](evidence.json.gz) contains exact raw records, receipts, suites, source states, compiler/Cargo/tool provenance and frozen harness snapshots. All archive member hashes were checked. Compiler/tool binaries and project caches are not included in this compact archive. Linked qualification bytecode is retained where required. No adoption decision or fresh-project result is implied by packaging this screen.
