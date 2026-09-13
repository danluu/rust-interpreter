# Stable per-MonoItem code-generation groups mechanism screen

Candidate median: 5.345366 s; baseline: 5.369589 s; independent baseline duplicate: 5.005032 s. 0 of five edited candidate commands were below 0.500 s. This single-history screen does not qualify the final latency target or holdout generalization.

Median paired wall change: +5.137%; CPU change: +12.658%. Maximum absolute A/A wall deviation: 6.899%; CPU deviation: 5.460%. These deviations describe the observed comparisons; they are not confidence intervals.

| Edit | Baseline wall s | Candidate wall s | Duplicate wall s | Baseline CPU s | Candidate CPU s | Duplicate CPU s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| combine-equal-and-supertype-widening-arms | 5.444075 | 5.723115 | 5.804765 | 7.755317 | 8.473336 | 8.178765 |
| collect-oneof-from-explicit-iterator | 5.369589 | 5.645413 | 4.999151 | 8.272070 | 8.123188 | 8.105391 |
| return-unrelated-widening-pair-early | 5.695532 | 5.345366 | 5.522341 | 7.827383 | 8.984461 | 7.796752 |
| express-subtype-test-with-is-some-and | 4.863053 | 5.239115 | 5.005032 | 7.665320 | 8.635602 | 7.872593 |
| make-union-pair-iterator-explicit | 4.770397 | 5.117468 | 4.904197 | 7.547376 | 8.685404 | 7.640417 |

Wall time includes the entire launcher, Cargo, VM, all 14 original tests and receipt I/O. Waited-child CPU may exceed wall time because compilers run concurrently. Nested stages remain separate; nothing is subtracted from complete-command time.

| Arm | Empty-target wall s | CPU s | All nine commands wall s |
| --- | ---: | ---: | ---: |
| baseline | 62.569633 | 179.692855 | 104.615887 |
| candidate | 64.680590 | 189.981231 | 108.493549 |
| duplicate | 64.492003 | 186.418559 | 106.832521 |

The one cold observation per arm includes its empty project cache; installed tools and prepared std MIR are separate setup. One cold observation does not establish a repeatable cold-build gain or regression.

All 27 commands, nine source states, five first-seen valid edited hashes per arm, all 14 original tests, deliberate wrong-result failures, compiled recovery and final restoration were checked. Outputs, outcomes, bytecode and entry catalogs agree across arms for every state. Source edits, manifests, features, units, profiles and checking requirements were preserved.

same compiler and tool binaries; module off/off/off; MonoItem off/on/off. The compiler binary, native std and exporter/VM are identical for off/on/off. This comparison does not attribute differences from a separately built public compiler to the patch.

[summary.json](summary.json) retains every pair, command, setup identity and artifact hash. [evidence.json.gz](evidence.json.gz) contains exact raw records, receipts, suites, source states, compiler/Cargo/tool provenance and frozen harness snapshots. All archive member hashes were checked. Compiler/tool binaries and project caches are not included in this compact archive. Linked qualification bytecode is retained where required. No adoption decision or fresh-project result is implied by packaging this screen.
