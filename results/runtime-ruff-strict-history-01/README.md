# Strict Ruff correctness history

The unchanged six-test Ruff batch passes with both diagnostic compatibility
policies disabled. HIR-off and HIR-on each pass the original source, all five
cumulative correct edits, and restored original source. Both modes reject the
wrong-edit batch. All eight off/on bytecode pairs match, and all 16 strict
bytecode artifacts also match their corresponding earlier diagnostic artifact.
All 11,119 source files (89,102,713 bytes) are restored.

This is one instrumented correctness history, not a latency qualification or a
global cache-coverage result. The development target is now qualified for this
strict batch; the edited-build 0.5-second goal has not been established.

The actual history has two owners. Strict03 completed the two original-source
primes, then its guard rejected the first intentional edit because registry.rs
had accidentally been frozen as immutable. That failed receipt and raw history
remain intact. Continuation02 reused the same two caches and performed exactly
14 remaining calls. Its source-state guard checks the reviewed digest on every
call, with the original bytes retained separately. Partial preparation01 is
also preserved: it produced no workload, and a separate read-only diagnosis
reproduced a str/Path digest mismatch. Its original process exit/output was not
retained; the observation explicitly records that limitation.

The platform helper keeps sysname, release, version and machine exact while
retaining hostname as context. Five bounded pure controls passed; source,
provider, installed-runtime, shared-std and tool guards were preserved.

The archive contains 1,388 logical members and 926 physical members using backward
content-deduplication links. Independent readback verified every member hash and
size, all 1,387 live frozen inputs, and full gzip EOF/CRC. Mutable derived caches
are excluded; exact initial/final catalogs, all selected copied artifacts,
compiler argv, dep-info, timings, raw commands, snapshots and failed proposals
are retained. Installed tool/source trees remain in place.

See `summary.json` for the outcome and scope, `manifest.json` for exact archive
membership, and `archive-execution.json` for actual retention process evidence
and independent full readback. The source/plan review receipts are included
separately alongside the archive. Frozen historical README/proposal text inside
the archive describes its status at preparation, not a later success claim.
