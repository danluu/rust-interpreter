# Reuse normalized local types and initialization shapes

Unqualified build-time candidate, recorded before edits or measurements.

- Base: `8325904a15fef9850f86a53122211ba51f8febd4` (the separate scalar-plan reuse candidate).
- Branch: `perf/reuse-local-layouts-20260912`.
- Owned worktree: `/Users/danluu/dev/rust-interp-build-plan-20260912`.
- No builds, tests, benchmark runs or shared-lock acquisition by the implementer.

`Lower::new` already normalizes every MIR local type and obtains its layout to
initialize frame slots. Retain those normalized types for this `Lower` only.
Collect the size/alignment shapes during that same loop and move the vector into
scalar packing and its existing chosen-layout certificate. Do not retain another
long-lived shape copy. Reuse the normalized type for scalar eligibility and
base-local place/operand types, leaving projected and constant normalization on
their original paths.

Keep the original layout lookup, unsized rejection, alignment rejection and frame
allocation order. Synthetic `Lower::empty` adapters initialize an empty type
vector; the type helper falls back to the original normalization when no cached
type exists. Hidden caller storage, temporary slots, scalar/aggregate algorithms,
the existing capture certificate and serialized cache payloads remain unchanged.
All initialization queries remain inside the same per-function dependency
observation closure. Green function-cache replay bypasses `Lower`; each fresh or
verification-fallback `Lower` owns its independent types.

Qualification must compare exact artifact bytes and diagnostics with the base,
including generic associated types at different integer widths, aligned and
zero-sized aggregates, field/index/deref projections, scalar lifetimes and
synthetic Result adapters. Root will schedule the focused fixture, retained
regression corpus and real-project paired build-time measurements. No speedup
or adoption claim is made by this source branch.

The focused fixture is `tests/local_layout_fixture.rs`, also registered in
`scripts/validate_interpreter.py` for native/interpreter/JIT comparison. Its
native entry checks an independent integer-only oracle, and its standalone Rust
test covers 257 consecutive inputs plus wide boundary values. The existing
Result-adapter and strict rejection fixtures remain part of that validation
script. Shapes are collected only when the existing local-count packing bound
permits them; functions above that bound retain only their normalized types.
