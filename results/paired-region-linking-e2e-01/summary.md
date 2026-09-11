# Linked blocks: paired production-edit commands

Each comparison runs the same production edit and original tests through native Rust, the previous qualified JIT, and the candidate JIT. Separate caches are used for the two immutable tool builds. Full subprocess times include Cargo, strict checking, export, launcher hashing, and execution. Artifact snapshots are copied after timing.

| Workflow | Native (s) | Baseline JIT (s) | Candidate JIT (s) | Median paired change (ms) | Candidate wins |
|---|---:|---:|---:|---:|---:|
| [fre-word64](../e2e-paired-fre-word64-region-linking-01/summary.md) | 2.377366 | 3.067055 | 2.628193 | -437.552 | 5/5 |
| [fre-word64-inline8](../e2e-paired-fre-word64-inline8-region-linking-01/summary.md) | 1.674748 | 2.285871 | 1.966325 | -315.828 | 5/5 |
| [pgrust-sha1-inline8](../e2e-paired-pgrust-sha1-inline8-region-linking-01/summary.md) | 0.760010 | 1.154865 | 0.971630 | -189.156 | 5/5 |

Every compared command executed identical bytecode, all original tests remain unchanged, and all modes reject the deliberately wrong production edit. Five paired edits on a shared host remain a small sample. Cold times, exact commands, all pairs, and Cargo/execution stages are retained in JSON. Bootstrap and reusable metadata-sysroot setup are excluded.

[Runtime comparison](../jit-region-linking-runtime-01/summary.md). [Validation](../jit-region-linking-validation-01.json).
