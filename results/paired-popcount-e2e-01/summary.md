# Population count: paired production-edit commands

This candidate is not retained. SHA-1 improves, but both paired word64 build/test workflows regress. The qualified call-copy build remains selected. The full nine-workflow corpus was not run for this rejected candidate.

Each comparison runs the same production edit and original tests through native Rust, the previous qualified JIT, and the candidate JIT. Separate caches are used for the two immutable tool builds. Full subprocess times include Cargo, strict checking, export, launcher hashing, and execution. Artifact snapshots are copied after timing.

| Workflow | Native (s) | Baseline JIT (s) | Candidate JIT (s) | Median paired change (ms) | Candidate wins |
|---|---:|---:|---:|---:|---:|
| [fre-word64](../e2e-paired-fre-word64-popcount-01/summary.md) | 1.783903 | 2.997153 | 3.045140 | 24.281 | 1/5 |
| [fre-word64-inline8](../e2e-paired-fre-word64-inline8-popcount-01/summary.md) | 1.799020 | 2.286140 | 2.323901 | 37.761 | 2/5 |
| [pgrust-sha1-inline8](../e2e-paired-pgrust-sha1-inline8-popcount-01/summary.md) | 0.764551 | 1.169735 | 1.157369 | -14.007 | 4/5 |

Every compared command executed identical bytecode, all original tests remain unchanged, and all modes reject the deliberately wrong production edit. Five paired edits on a shared host remain a small sample. Native still wins these compute-heavy workflows. Cold times, exact commands, all pairs, and Cargo/execution stages are retained in JSON. Bootstrap and reusable metadata-sysroot setup are excluded.

[Runtime comparison](../jit-popcount-runtime-01/summary.md). [Validation](../jit-popcount-validation-01.json).
