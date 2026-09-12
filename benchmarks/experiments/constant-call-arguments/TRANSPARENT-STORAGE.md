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

The second bounded batch contains the two completed entropy-AA diagnostic JSON
profiles, budget-register-smoke-05 profiles1/3/11/13, and code.bin/map.json from
each of the six completed selected-native block/exhaustive sample processes.
Bind every file to its successful producer receipt and existing content digest.
These are diagnostic outputs, never timed runtime inputs. Apply the same
single-file staging, byte/metadata equality and3GiB reserve rules. This batch
restores host-build headroom without lowering build admission or removing data.

The third bounded batch preserves16 public diagnostic JSON profiles: the two
aggregate-reuse collection profiles; budget-register randomness and token
transition profiles; and profiles1/3/11/13 from call-slot-smoke-01,
whole-call-runtime-smoke-01 and budget-register-smoke-04. Every file has an
existing digest and terminal producer receipt. The last controller terminated
with return1 because independent entropy caused cross-process counter mismatch;
its individual profile commands all returned0. Verify that exact recorded
failure and the report-bound commands file; preserve its failed classification.
No private profiles, source, binaries, benchmark inputs or caches are included.
All previous byte/metadata equality, single-copy staging and reserve rules apply.

The fourth batch covers the successful profiling commands in the ten exact
public diagnostic runs listed in legacy_profiles.py, plus six completed native
PC maps. These older runs have terminal child receipts instead of supervisors.
Require the recorded root cwd, completed commands, no matching live processes
and no open files. Preserve their original summary classifications. Some old
profile commands bind an output path without a digest: record and preserve its
current bytes, explicitly distinguishing this from historical hash validation.
The four drift profiles and six PC maps retain their historical hash checks.
Only diagnostic JSON outputs are compressed; no benchmark inputs, source,
executables, tool libraries, caches or private data enter this batch. Keep the
same staging, metadata equality, atomic replacement and3GiB reserve rules.
