# Standard-library MIR prepared with the installed native runtime

The ordinary explicit-runtime std CLI completed once in the runtime's existing
owner checkout. Runtime key `eca3d1317ba4c852d64de435aa0f0e5d87ae63bd4eb96cfafacc7b0a85841d03`
produced shared source-paths-v2 std key
`e4d1cd29bf4dbac5f9cbf6a92c77a562b89f7079c4474653f180346a00f24b63`.
All seven direct child commands passed their expected return codes, including
both E0080 source-location probes. Setup used pinned offline Cargo and two build
jobs under the canonical workload lock with the reviewed 16/9/8 GiB guards.

The cold metadata build took 10.3514 seconds and complete admitted setup took
16.4484 seconds, producing 112,867,217 metadata bytes. These are setup timings;
they do not measure an edited application build or establish the 0.5-second
target. Full diagnostic presentation and application integration remain
unqualified.

Independent saved-output verification checked all seven command, environment,
working-directory, parent/PID and time associations, plus all 125 original and
retained input files. It rehashed all 3,644 source copies, 3,670 published std
files and 19 evidence files, checking exact readonly stamps and single-link
ordinary copies. Root independently repeated the output checks. The first
additional audit helper used the wrong JSON whitespace when reconstructing the
std key; its source and failure receipt are retained. The corrected audit read
the same completed artifacts successfully. No compiler or std setup was rerun.

The archive contains the frozen controller/plan, source and executor copies,
complete setup records, actual stdout/stderr captured in per-command JSON,
immutable readiness and evidence records, and both audit versions. It excludes
native-runtime and std payload copies. Every one of its 189 logical members was
read back and hashed, and gzip was read through EOF to check its complete CRC.
Identical proof payloads use backward tar links. The nine separate archival
execution files retain the exact launch environment and completed supervisor
association; `archive-execution.json` binds their readback hashes.

The source commit recorded in the archive is the base checkout before these
new frozen controller files were committed. Their exact bytes are bound by the
retained input manifests. Historical setup freezes must be read from retained
copies after the owner checkout advances; installed runtime and std roots stay
immutable.
