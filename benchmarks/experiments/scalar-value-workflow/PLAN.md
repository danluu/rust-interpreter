Compare the qualified full scalar compiler/runtime with the retained production
tool on actual source edits. Use the exact production wrapper on both sides.
Candidate ba4ad407 is a component composition: VM/exporter from source key
aa56492e plus wrapper from production key 9637b0ac. Its key hashes canonical
composition JSON; it is explicitly not a legacy Rust source key. Cargo routing
and publication repeat all nineteen checks on this exact composition. The
compiler/runtime bytes are identical to those already qualified on both real
test batches; no new source transformation is introduced by composition.

Use the qualified scalar-value-cargo-controlled/launcher.py on both sides,
with scalar disabled in both A/A modes and enabled only for the candidate in
the actual comparison. The staged existing harness adds scalar config,
command/receipt/header validation and exact phase-key guards. Existing asserts,
source edits, original tests, negative edit controls, source restoration,
timers, CPU accounting, source histories and mode order remain.

Fixed fresh order: A/A folded, A/A token, candidate folded, candidate token.
Each history has three cycles, five actual edits, 63 primary commands, 21 Cargo
checks, 15 edited pairs and 42 distinct artifact snapshots. Keep native
o0-incremental/jobs18/default test threads, custom jobs4, original guest MIR
flags, pinned std MIR, entropy and all workflow/case/source hashes.

Token must improve complete-command wall time at least 10%, beyond the fresh
A/A envelope, while CPU improves. Folded keeps independent 5% wall/CPU guards.
All observations remain. Seven held-outs follow only a primary pass. No
unchanged-build metric, instruction-count substitution or fastest-native claim.
Runtime options and missing general threads/unwinding/FFI remain explicit.

Qualify the staged harness, new scalar checks, exact component admission and
preservation of the old verifier before timings. Preserve 8 GiB at every command
and admit full storage requirements before starting; no cache maintenance during
timed histories. Retire only separately inventoried and verified completed
caches if needed. No unrelated processes or private outputs are touched.
