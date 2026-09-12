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

Ruff now passes all twelve commands, including the expected missing-catalog
rejection. Qualify the catalog across the complete pgrust source-edit sequence,
preserving the catalog beside each bytecode snapshot and matching the executed
function IDs to it. Retained pgrust native/check caches occupy 1.2 MiB/32 KiB
and all fourteen artifacts total 2.5 MiB; admit this small correctness sequence
at 8.125 GiB, retaining the 8 GiB check before every child. This is a catalog
correctness follow-up, not a repetition to promote the earlier performance
result. Freeze this plan with the controller and tools.

Pgrust's 32-command follow-up passes, including sixteen retained artifact/catalog
pairs and the restored source. The first attempt stopped at its initial disk
admission check before starting any child; retain that receipt. Finish with a
fresh fre folded-trie export at the exact final edited source of its retained
native oracle. Reuse the real-export controller, run all eighteen native tests,
then ordinary/fresh/prepared custom execution with controlled entropy. The
completed fre cache inventory is 43.8 MiB excluding incremental state; admit one
nonincremental export at 8.25 GiB and keep the 8 GiB per-child floor. This check
uses one real edited source and a retained native executable; it is not a new
edit-loop performance measurement or a replacement for the full pgrust sequence.
