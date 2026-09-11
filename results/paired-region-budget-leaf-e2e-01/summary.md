# Rejected budget-register leaf frame: paired production-edit commands

Rejected. The candidate loses all ten word64 pairs and gives no material SHA-1 benefit. No nine-workflow corpus was run for this variant.

Each comparison runs the same production edit and original tests through native Rust, the previous qualified JIT, and the candidate JIT. Separate caches are used for the two immutable tool builds. Full subprocess times include Cargo, strict checking, export, launcher hashing, and execution. Artifact snapshots are copied after timing.

| Workflow | Native (s) | Baseline JIT (s) | Candidate JIT (s) | Median paired change (ms) | Candidate wins |
|---|---:|---:|---:|---:|---:|
| [fre-word64](../e2e-paired-fre-word64-region-budget-leaf-01/summary.md) | 1.921698 | 2.634337 | 2.694724 | 54.916 | 0/5 |
| [fre-word64-inline8](../e2e-paired-fre-word64-inline8-region-budget-leaf-01/summary.md) | 1.605604 | 1.882190 | 1.907683 | 18.784 | 0/5 |
| [pgrust-sha1-inline8](../e2e-paired-pgrust-sha1-inline8-region-budget-leaf-01/summary.md) | 0.762701 | 0.990620 | 0.988057 | -1.145 | 3/5 |

Every compared command executed identical bytecode, all original tests remain unchanged, and all modes reject the deliberately wrong production edit. Five paired edits on a shared host remain a small sample. Cold times, exact commands, all pairs, and Cargo/execution stages are retained in JSON. Bootstrap and reusable metadata-sysroot setup are excluded.

[Runtime comparison](../jit-region-budget-leaf-runtime-01/summary.md). [Validation](../jit-region-budget-leaf-validation-01.json).
