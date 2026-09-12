# Stable selected entries after optimization

The Ruff pilot passes six individual native tests and both ordinary VM batches,
then rejects the optimized batch root before isolated execution. Root instruction
shape is not a stable test descriptor. Preserve explicit selected function IDs
before call optimization and publish an entry catalog beside the exact Cargo
bytecode sidecar. The existing optimization pipeline retains function IDs.

Bind the catalog to the bytecode SHA-256, target, version and original entry.
Retain requested names and the final body name for each ID, including Result
adapters. Require distinct, valid zero-argument/unit-result entries. Do not
recover a missing catalog by guessing function names or interpreting optimized
root instructions more permissively. Old artifacts may still use the existing
strict legacy descriptor path; new exporter capabilities let the launcher select
the catalog automatically. The Program wire format and ordinary execution stay
unchanged. Catalogs do not yet add libtest discovery, ignore or panic semantics.

Compute an artifact digest once when publishing related sidecars. The VM must
verify the catalog against the bytes it actually decoded before creating the
suite report or executing any guest body. The Cargo launcher also verifies the
requested name sequence under its existing invocation lock. Reject stale,
truncated, oversized, duplicate, out-of-range and mismatched catalogs, including
same-sized bytecode changes and changed entry signatures.

Qualify Rust workspace debug/release tests and Python launcher controls. Include
a root altered by actual call optimization, Result adapters, failure followed by
success, and malformed catalog rejection before guest side effects. Then export
and run real pgrust/fre edits, and repair the Ruff coverage failure with an actual
exported catalog when storage admits the frontend build. Preserve the failed
Ruff attempt. Keep the 8 GiB floor, two workers and 45-second lock waits.

The real Rust fixture passes all sixteen commands, including a Result adapter,
an optimized root, wrong-edit failures and an unselected borrow error. Next
re-export Ruff at the exact final source state of its retained native oracle,
then compare native assertions and fresh/prepared execution using the actual
new catalog. Run one custom Cargo export with incremental storage disabled;
this is correctness coverage, with no native rebuild or timing comparison.
The earlier Ruff cache inventory is 514.6 MiB after retiring incremental state;
admit this metadata export at 8.75 GiB free and preserve the 8 GiB per-child
floor. Run native tests individually, record/replay guest entropy for isolated
equality, and verify that omitting the catalog reproduces the format rejection.
Restore the original source. Preserve this setup's profile difference explicitly.
