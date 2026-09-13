# Cargo compiler-info cache mechanism screen

Candidate median: 4.048810 s; baseline: 4.125076 s; independent baseline duplicate: 4.244661 s. 0 of five edited candidate commands were below 0.500 s. This single-history screen does not qualify the final latency target or holdout generalization.

Median paired wall change: -2.877%; CPU change: +0.437%. Maximum absolute A/A wall deviation: 5.120%; CPU deviation: 2.715%. These deviations describe the observed comparisons; they are not confidence intervals.

| Edit | Baseline wall s | Candidate wall s | Duplicate wall s | Baseline CPU s | Candidate CPU s | Duplicate CPU s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| combine-equal-and-supertype-widening-arms | 4.119794 | 4.207936 | 4.330736 | 6.736018 | 6.820385 | 6.761999 |
| collect-oneof-from-explicit-iterator | 4.077741 | 3.948882 | 4.283694 | 7.397809 | 7.206752 | 7.310741 |
| return-unrelated-widening-pair-early | 4.177696 | 4.048810 | 4.146445 | 6.851813 | 6.744195 | 6.862972 |
| express-subtype-test-with-is-some-and | 4.216398 | 4.165466 | 4.244661 | 7.153452 | 7.240078 | 7.347659 |
| make-union-pair-iterator-explicit | 4.125076 | 4.006385 | 4.112202 | 6.812994 | 6.842784 | 6.832147 |

Wall time includes the entire launcher, Cargo, VM, all 14 original tests and receipt I/O. Waited-child CPU may exceed wall time because compilers run concurrently. Nested stages remain separate; nothing is subtracted from complete-command time.

| Arm | Empty-target wall s | CPU s | All nine commands wall s |
| --- | ---: | ---: | ---: |
| baseline | 58.432857 | 166.119665 | 92.031522 |
| candidate | 59.231371 | 171.874007 | 92.119307 |
| duplicate | 62.088075 | 181.983071 | 96.006769 |

The one cold observation per arm includes its empty project cache; installed tools and prepared std MIR are separate setup. One cold observation does not establish a repeatable cold-build gain or regression.

All 27 commands, nine source states, five first-seen valid edited hashes per arm, all 14 original tests, deliberate wrong-result failures, compiled recovery and final restoration were checked. Outputs, outcomes, bytecode and entry catalogs agree across arms for every state. Source edits, manifests, features, units, profiles and checking requirements were preserved.

same public compiler/exporter/VM; matched stock/candidate/stock Cargo. The matched Cargo executables differ only by the qualified production-source change, with equal build settings and dynamic libraries. Cargo optimization is isolated from custom compiler policies.

[summary.json](summary.json) retains every pair, command, setup identity and artifact hash. [evidence.json.gz](evidence.json.gz) contains exact raw records, receipts, suites, source states, compiler/Cargo/tool provenance and frozen harness snapshots. All archive member hashes were checked. Binaries and project caches are not included in this compact archive. No adoption decision or fresh-project result is implied by packaging this screen.

The baseline cold command overlapped a mistakenly locally locked mocked test process for 0.104432 s. No edited sample overlapped, and no observations were replaced. That runner's serialization claim was withdrawn and its current tests were repeated under the canonical lock. [Setup and admission evidence](setup-and-admission.json) retains this overlap, setup receipts, and the saved-assessor JSON-normalization fix with 16 passing boundary tests.
