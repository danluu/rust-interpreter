# Qualify one aggregate graph against the projection oracle

Model03 adds ordered return lanes to the shared scalar graph. All lanes root their
values in the same liveness traversal; computation, control flow and original
PC accounting happen once. The small-result representation remains the existing
single Return value. Full bytes are available from the reference evaluator.

Every prior aggregate fixture now compares the combined graph with its independent
projections and ordinary bytecode interpreter, retaining the full-byte copy oracle,
padding, branch, fault and budget checks. A ninth test requires aggregate plans to
be rejected by both legacy native entry points and verifies identical small-result
native words in profiled and unprofiled modes. The register allocator accounts
for every return lane's use, although no aggregate native ABI is enabled yet.

Run nine controls in debug/release plus the same 13 memory-proof and five scalar
controls in release. The test-only combined entry retains the 1 KiB frame,
64-byte result and existing argument/register/operation/work bounds. No aggregate
native publication or original guest benchmark. Native ABI work starts only after
these controls and actual combined-plan eligibility are checked.
