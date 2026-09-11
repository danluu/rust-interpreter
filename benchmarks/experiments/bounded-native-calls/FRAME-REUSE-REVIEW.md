# Constraints on a possible frame-reuse experiment

This is a source review during the frozen persistent-register E2E run. It does
not select a new runtime change before that run finishes or estimate a speedup.
The existing unused-local and argument-zeroing censuses remain valid; do not
repeat them under a new name.

`lower/scalar_frame.rs` already colors private primitive MIR locals with
full-CFG liveness, dead-write interference and an independent coloring check.
It excludes entry-zero reads, ABI locals, addresses, projections and call
destinations. `lower/scalar_promote.rs` then removes some of their memory
accesses. The next frame opportunity would have to cover additional storage,
not merely repeat scalar coloring or inline scratch-bank reuse.

Extending the current type predicate to aggregates is insufficient. A MIR
assignment can initialize fields while leaving padding or inactive enum bytes
unchanged. Two equal-size/equal-alignment locals can disagree about which bytes
they overwrite. Sharing their slots can copy stale bytes into a later argument,
return value or larger copy, even when the named MIR values do not interfere.
The current engine provides zero-initialized frames; a value-liveness proof
alone does not preserve that byte contract.

The lowerer currently ignores StorageLive/StorageDead. Reusing a scope requires
handling loops, joins, address escapes and reads through derived pointers;
inserting zero fills at every StorageLive could also increase work. Call-result
definitions apply on a normal return edge, not an unwinding/fault edge. The
existing conservative treatment of Call destinations cannot simply be removed.

A useful next diagnostic, if fresh E2E/profile evidence still favors frames,
would measure **provably private, fully overwritten ranges with nonoverlapping
lifetimes**, weighted by the actual profiled function identities/call counts.
Start with explicit byte-layout classes: private primitive arrays with complete
initialization; then projected/partial stores, padding, enums, address-taking,
ABI values and call destinations as distinct exclusions. Count each physical
range once after existing coloring. Preserve compiler instance identities;
rendered names can collide. Bound graph/set work and report declines. This is a
new reuse-scope question, separate from whether a declaration is unused.

Before implementing reuse, require substantial additional weighted scope and
an explicit initialization/escape argument. Test dead stores into another live
value, partial-field writes, array elements, branch joins, repeated lifetimes,
aliased copies, padding propagation, call outcomes and address observations.
Keep the full existing differential corpus. A layout change intentionally
changes bytecode, so the benchmark needs a separate changed-artifact comparison
with unchanged Rust sources/assertions and explicit native reference outputs;
do not relax the identical-artifact check for the current runtime experiment.

If this scope is small, revisit a broader interruptible native-call design or
frontend/artifact reuse using measured command stages. Avoid another sequence
of narrowly justified zero/copy emitter tweaks without complete-command gains.
