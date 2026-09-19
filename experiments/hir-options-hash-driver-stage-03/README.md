# Corrected hash-driver continuation

Source proposal only; no candidate application timing or driver qualification.
The original first driver attempt remains failed after one E0277 compilation;
its immutable source, raw diagnostics, receipts and retained snapshots remain
at their original paths. The new driver wraps the standard Barrier in rustc's
existing IntoDynSyncSend wrapper, preserving the rendezvous, distinct-worker
assertion, repeated first access and all eight option contexts in each mode.

The new attempt uses fresh driver02 artifacts/evidence. It authenticates the
independent failed-owner audit and reconstructs its entire snapshot catalog,
including every alias and full gzip EOF/hash readback. A failed catalog owner
never becomes a successful workload. The combined 70-control qualification is
required before importing the new catalog and plan-reference readers.

The plan stores one exact authenticated reference to its already frozen
metadata document. Full typed reconstruction is checked before reading any
plan field; the raw plan digest remains the packet association. No metadata,
provider byte, source input, original failed evidence or capacity charge is
removed. The 256 MiB evidence limit and 40 MiB remaining reservation are fixed.

Copied test_admission/test_controls/test_file_table_audit/test_native_wrapper/
test_prerequisites/test_snapshot_bindings preserve the preceding stage's source
context. They have not been rerun against this successor; original qualified
control records retain their original source associations. The new focused
controls are catalog02's 33 original and 25 failed-owner controls plus the 12
plan-reference controls. Actual results must be reported separately.
