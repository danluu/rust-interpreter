# Private aggregate frame relocation: complete primary edit benchmarks

| Workflow | Paired wall change | Paired CPU change | Native median | Control median | Candidate median | Gate |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| folded-literal-trie | -12.77% | -12.89% | 1.702s | 1.939s | 1.696s | pass |
| token-phrase | +3.70% | +3.33% | 1.965s | 4.290s | 4.462s | pass |

Both primary gates pass. Proceed to fresh broad native/TLS/fre qualification and all seven held-outs; do not retain the compiler change before those pass.

All 168 commands, 30 edited pairs and 84 artifact hashes verify. These are real production-source edits, including wrong-edit rejection and source restoration; no unchanged-build timings enter the paired result. Three cycles rotate mode order. Native/check controls are retained. Only the exporter changes between custom modes: VM, wrapper, frontend flags and runtime options match. Candidate times include all added analysis and relocation work.

Artifacts can differ across this compiler transformation. Original assertions and focused differentials pass; this does not formally prove semantic equivalence or full Rust support. Three cycles on a shared host are descriptive, not independent statistical trials. Setup and target-cache-cold commands are recorded separately.
