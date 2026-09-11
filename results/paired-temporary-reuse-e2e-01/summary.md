# Scratch-register reuse: paired production-edit commands

Each comparison runs the same production edit and original tests through native Rust, the previous qualified JIT, and the candidate JIT. Separate caches are used for the two immutable tool builds. Full subprocess times include Cargo, strict checking, export, launcher hashing, and execution. Artifact snapshots are copied after timing.

| Workflow | Native (s) | Baseline JIT (s) | Candidate JIT (s) | Median paired change (ms) | Candidate wins |
|---|---:|---:|---:|---:|---:|
| [fre-word64](../e2e-paired-fre-word64-temporary-reuse-01/summary.md) | 1.922219 | 2.673083 | 2.736060 | 37.609 | 0/5 |
| [fre-word64-inline8](../e2e-paired-fre-word64-inline8-temporary-reuse-01/summary.md) | 2.305482 | 2.249242 | 2.236591 | -7.008 | 3/5 |
| [pgrust-sha1-inline8](../e2e-paired-pgrust-sha1-inline8-temporary-reuse-01/summary.md) | 0.776978 | 1.021091 | 0.998363 | -0.147 | 3/5 |

Every compared command executed identical bytecode, all original tests remain unchanged, and all modes reject the deliberately wrong production edit. Five paired edits on a shared host remain a small sample. Cold times, exact commands, all pairs, and Cargo/execution stages are retained in JSON. Bootstrap and reusable metadata-sysroot setup are excluded.

[Runtime comparison](../jit-temporary-reuse-runtime-01/summary.md). [Validation](../jit-temporary-reuse-validation-01.json).

Candidate rejected after the full-command comparison: 6/15 paired wins, including 0/5 on default word64. Sources and mutable binaries were restored to qualified build `0d0d7b90`. Candidate sources, immutable tools, and every raw sample remain available.
