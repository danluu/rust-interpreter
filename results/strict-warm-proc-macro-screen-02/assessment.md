# Host proc-macro code generation mechanism screen

Candidate median: 4.040219 s; baseline: 4.083314 s; independent baseline duplicate: 4.009324 s. 0 of five edited candidate commands were below 0.500 s. This single-history screen does not qualify the final latency target or holdout generalization.

Median paired wall change: -1.433%; CPU change: -0.631%. Maximum absolute A/A wall deviation: 16.229%; CPU deviation: 6.825%. These deviations describe the observed comparisons; they are not confidence intervals.

| Edit | Baseline wall s | Candidate wall s | Duplicate wall s | Baseline CPU s | Candidate CPU s | Duplicate CPU s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| combine-equal-and-supertype-widening-arms | 4.244559 | 4.159487 | 4.933423 | 6.822803 | 6.779739 | 7.288464 |
| collect-oneof-from-explicit-iterator | 3.980456 | 3.923434 | 3.995831 | 7.310213 | 7.301160 | 7.262362 |
| return-unrelated-widening-pair-early | 4.083314 | 4.040219 | 4.009324 | 6.841058 | 6.874789 | 6.765004 |
| express-subtype-test-with-is-some-and | 4.272739 | 4.051578 | 4.060161 | 7.380914 | 7.055526 | 7.021881 |
| make-union-pair-iterator-explicit | 4.042875 | 4.005669 | 3.904993 | 6.959800 | 6.732300 | 6.739900 |

Wall time includes the entire launcher, Cargo, VM, all 14 original tests and receipt I/O. Waited-child CPU may exceed wall time because compilers run concurrently. Nested stages remain separate; nothing is subtracted from complete-command time.

| Arm | Empty-target wall s | CPU s | All nine commands wall s |
| --- | ---: | ---: | ---: |
| baseline | 59.605493 | 168.094510 | 95.455846 |
| candidate | 64.467450 | 194.476127 | 98.747564 |
| duplicate | 60.463657 | 175.524461 | 96.659964 |

The one cold observation per arm includes its empty project cache; installed tools and prepared std MIR are separate setup. One cold observation does not establish a repeatable cold-build gain or regression.

All 27 commands, nine source states, five first-seen valid edited hashes per arm, all 14 original tests, deliberate wrong-result failures, compiled recovery and final restoration were checked. Outputs, outcomes, bytecode and entry catalogs agree across arms for every state. Source edits, manifests, features, units, profiles and checking requirements were preserved.

same public compiler/Cargo/exporter/VM; host proc-macro codegen off/on/off. The compiler, Cargo, exporter, VM and prepared standard library are identical for off/on/off. Only eligible host proc-macro targets receive the explicitly recorded code-generation policy; application profiles and checking remain unchanged.

[summary.json](summary.json) retains every pair, command, setup identity and artifact hash. [evidence.json.gz](evidence.json.gz) contains exact raw records, receipts, suites, source states, compiler/Cargo/tool provenance and frozen harness snapshots. All archive member hashes were checked. Binaries and project caches are not included in this compact archive. No adoption decision or fresh-project result is implied by packaging this screen.
