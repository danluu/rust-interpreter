# Preserve readable evidence while reducing allocated storage

Use macOS ditto's documented filesystem-compression option on exactly the seven
completed suite-profiling-real-01 JSON profiles and token artifacts from the
completed constant-specialize-saved-01/02/03 runs. These task-owned regular files
are about254MiB uncompressed. Do not touch source, tools, build caches, private
data, the retained baseline bytecode, or any running workload.

Serialize with the benchmark lock and verify each producer's terminal receipt
and expected input hash. Stage a compressed copy beside each original with
`ditto --hfsCompression --noclone`. Verify its full SHA256, logical length, mode,
owner/group, modification timestamp and all file flags except the compression
flag. Only after validation and a measured allocation reduction, atomically
replace that exact original and recheck it. Preserve every original pathname
and logical byte; there is no archive and readers need no extraction step.

Require3GiB free before each copy. At most one file is staged at once (largest
75MiB). Failure leaves the original in place and preserves the attempted copy
for inspection. Report physical allocation savings separately from host free
space, which unrelated work can change. Compression changes I/O representation;
this is maintenance, not a latency measurement or a source of benchmark gains.
The parked candidate artifacts are not scheduled for further timing.
