# Scalar value ABI: short real-edit screen

The candidate is parked: token missed the predeclared 8% screening target.
The full A/A and held-out histories will not run for this candidate.

| Workload | Paired wall change | Paired CPU change | Native median | Control median | Scalar median |
| --- | ---: | ---: | ---: | ---: | ---: |
| token-phrase | -0.74% | -2.66% | 2.304s | 5.103s | 5.031s |
| folded-literal-trie | -0.41% | +1.07% | 2.007s | 2.228s | 2.070s |

Each workload has five actual production edits, original assertions and a wrong-edit rejection in every mode: 42 primary commands, 14 independent Cargo checks and 28 executed snapshots in total. All verification passed. Five correlated edit pairs are screening evidence, not a precise estimate of a small effect. The deployed tool stays unchanged.

Token guest-process execution saves 170ms at the median paired difference, while Cargo adds 144ms. The scalar proof/finalization timer is about 73ms in the first token edit; it is included in lowering, not an additional stage. Fewer copy instructions did not produce a useful complete-command improvement.

Recorded launcher costs also constrain the next work: tool lookup/hashing is about 2ms, std-MIR lookup 36–38ms, artifact hashing about 10ms and call-report validation about 12ms. Optimizing these alone cannot close the multi-second token/native gap. Exporter lowering is 0.858s control / 0.935s scalar; frontend about 0.65–0.67s. These measurements prioritize lowering/export attribution over another emitter micro-optimization.

The next experiment measures export passes and publication on the retained compiler, with exact output identity and strict error controls. Separately qualify a tuned native control before interpreting project-wide speedups. Preserve the scalar source branch for later register-allocation work; do not retry this same screen.

The executable wrapper is identical on both sides. Scalar source `840fdb5/aa56492e` is executed via composed tool `ba4ad407`. Native uses O0/incremental, 18 jobs/default test threads; custom uses four jobs. Absolute times from this shared-host session must not be compared with historical medians as a version speedup.
