# Frame initialization census

This standalone Rust analyzer uses typed bytecode and the retained local-call
proof to count argument copies into newly zeroed frames. It makes no guest
transformation. The Cargo workspace is separate from the production tool
fingerprint.

`python3 benchmarks/experiments/frame-initialization/run.py` builds and analyzes
the two recorded local artifacts/profiles, under the benchmark lock. Its fresh
output directory is `.work/frame-initialization-census-01`; use a new directory
for another run. Inputs and source hashes are recorded. Existing runs are never
overwritten. The local `.work` artifacts are not included in Git.

[Result and limitations](../../../results/frame-initialization-census-01/summary.md).
