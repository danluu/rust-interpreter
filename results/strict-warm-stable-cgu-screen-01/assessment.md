# Stable code-generation groups mechanism screen

**No warm-build improvement; the 0.5-second target is not met.** This preliminary screen used an optimized custom compiler with its own assertions enabled. Its [integration controls](../custom-compiler-integration-03/README.md) passed, but 18 standard-library diagnostic snippet gaps remain. The explicitly source-derived diagnostic comparison is not full presentation qualification, and this result is ineligible for final latency or adoption. [Admission and scope evidence](qualification-context.json).

Candidate median: 5.167313 s; baseline: 5.158377 s; independent baseline duplicate: 5.170138 s. 0 of five edited candidate commands were below 0.500 s. This single-history screen does not qualify the final latency target or holdout generalization.

Median paired wall change: +0.415%; CPU change: -0.257%. Maximum absolute A/A wall deviation: 0.909%; CPU deviation: 1.881%. These deviations describe the observed comparisons; they are not confidence intervals.

| Edit | Baseline wall s | Candidate wall s | Duplicate wall s | Baseline CPU s | Candidate CPU s | Duplicate CPU s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| combine-equal-and-supertype-widening-arms | 5.248260 | 5.245891 | 5.219827 | 8.654242 | 8.614016 | 8.678111 |
| collect-oneof-from-explicit-iterator | 5.009779 | 5.140573 | 5.021451 | 8.786183 | 9.037382 | 8.849978 |
| return-unrelated-widening-pair-early | 5.217561 | 5.167313 | 5.170138 | 8.579467 | 8.520612 | 8.537494 |
| express-subtype-test-with-is-some-and | 5.158377 | 5.194343 | 5.203900 | 8.608755 | 8.728884 | 8.770678 |
| make-union-pair-iterator-explicit | 4.949201 | 4.969755 | 4.992933 | 8.173918 | 8.152886 | 8.164524 |

Wall time includes the entire launcher, Cargo, VM, all 14 original tests and receipt I/O. Waited-child CPU may exceed wall time because compilers run concurrently. Nested stages remain separate; nothing is subtracted from complete-command time.

| Arm | Empty-target wall s | CPU s | All nine commands wall s |
| --- | ---: | ---: | ---: |
| baseline | 74.591631 | 230.952168 | 115.494271 |
| candidate | 74.885761 | 239.684612 | 115.866418 |
| duplicate | 75.675986 | 242.202508 | 116.670166 |

The one cold observation per arm includes its empty project cache; installed tools and prepared std MIR are separate setup. One cold observation does not establish a repeatable cold-build gain or regression.

All 27 commands, nine source states, five first-seen valid edited hashes per arm, all 14 original tests, deliberate wrong-result failures, compiled recovery and final restoration were checked. Outputs, outcomes, bytecode and entry catalogs agree across arms for every state. Source edits, manifests, features, units, profiles and checking requirements were preserved.

same compiler and tool binaries; stable-CGU off/on/off. The compiler binary, native std and exporter/VM are identical for off/on/off. This comparison does not attribute differences from a separately built public compiler to the patch.

[summary.json](summary.json) retains every pair, command, setup identity and artifact hash. [evidence.json.gz](evidence.json.gz) contains exact raw records, receipts, suites, source states, compiler/Cargo/tool provenance and frozen harness snapshots. All archive member hashes were checked. Binaries and project caches are not included in this compact archive. No adoption decision or fresh-project result is implied by packaging this screen.
