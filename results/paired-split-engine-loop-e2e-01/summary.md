# Separate host engine loops: paired production-edit commands

Each comparison runs the same production edit and original tests through native Rust, the previous qualified JIT, and the candidate JIT. Separate caches are used for the two immutable tool builds. Full subprocess times include Cargo, strict checking, export, launcher hashing, and execution. Artifact snapshots are copied after timing.

| Workflow | Native (s) | Baseline JIT (s) | Candidate JIT (s) | Median paired change (ms) | Candidate wins |
|---|---:|---:|---:|---:|---:|
| [fre-word64](../e2e-paired-fre-word64-split-engine-loop-01/summary.md) | 1.994633 | 2.682204 | 2.658670 | 10.101 | 2/5 |
| [fre-word64-inline8](../e2e-paired-fre-word64-inline8-split-engine-loop-01/summary.md) | 2.548050 | 2.292517 | 2.368759 | -76.752 | 3/5 |
| [pgrust-sha1-inline8](../e2e-paired-pgrust-sha1-inline8-split-engine-loop-01/summary.md) | 0.931134 | 1.253745 | 1.295552 | 41.807 | 1/5 |

Every compared command executed identical bytecode, all original tests remain unchanged, and all modes reject the deliberately wrong production edit. Five paired edits on a shared host remain a small sample. Cold times, exact commands, all pairs, and Cargo/execution stages are retained in JSON. Bootstrap and reusable metadata-sysroot setup are excluded.

[Runtime comparison](../split-engine-loop-runtime-01/summary.md). [Validation](../split-engine-loop-validation-01.json).

Candidate rejected: 6/15 complete-command wins and a consistent word64 interpreter regression. The original qualified source and both mutable binaries were restored exactly; all candidate artifacts and raw samples remain.
