# First host-library build qualification failure

The first host-library candidate build reached all nine planned commands and
failed its final real-history qualification. It published no toolset and ran no
performance screen. The retained source is the original candidate, before the
separate parser correction and build02 retry.

| Check | Recorded outcome |
| --- | --- |
| Rust workspace tests | 504 passed, 2 ignored |
| Release tool build and capability probes | Passed |
| Launcher and publication Python unit tests | 10 passed |
| Real native/library histories | 2 passed, 1 failed |

The shared-library Cargo history failed because the candidate's strict argument
parser rejected Cargo's ordinary `-Z embed-metadata=no` argument on a native host
library invocation. Cargo exited 101 after the wrapper exited 2. The rejection
message, complete argv and source are retained. The other two histories passed:
native debug/overflow/UB configuration with generics, inlining and drop effects;
and uncalled type/borrow/const failures with source-position changes and
restoration. Passing those histories does not qualify the failed shared-library
history or establish a performance improvement.

`evidence.tar.xz` contains all nine exact command receipts and stdout/stderr,
completed setup metadata, original outer-supervisor plan/status/logs, and the
build01 source/harness/provenance payload. Its copied 173 workspace files and 133
harness files are verified against frozen plan01 hashes. The archiver uses these
retained snapshots rather than the live HOSTLIB source, which was intentionally
changed for the retry. The original plan retains its pre-execution
`not-executed` field; the failed supervisor and command receipts establish what
actually happened.

Each real fixture retains its source snapshots, command/output/environment JSONL,
original wrapper traces and final compiler NUL-argv records. Bytecode copied by
the partial history before failure is included as lossless base64 JSON envelopes
with raw source path, size and SHA256. Those envelopes are explicitly marked as
created during archival; they do not imply that a published provenance payload
or full off/on bytecode comparison completed. Target directories, native/tool
binaries and caches are excluded and remain untouched in the original attempt.

`members.json` records every member's original path, size and SHA256.
`summary.json` records archive identity, outcomes, fixture counts and bytecode
envelope identities. `packaging-receipt.json` records canonical-lock admission,
process ownership and completion. Every member, frozen snapshot and retained
bytecode source is rechecked before success. Command/output hashes first created
by this archive describe the retained files at archival time; the original
receipts are preserved verbatim.

Archival runs no compiler, tests or benchmarks and makes no changes to build01,
build02, application sources, standard-library preparation or installed tools.
