# Bound ownership of retained emission plans

Replace retained local-fill and call-slot BTree maps with sorted owned vectors;
keep analysis in its original order, then binary-search exact hint keys during
emission. Count all retained vector capacities, nested masks/argument hints,
boxed range plans and inline analysis in a checked payload charge.

Qualify a per-JIT plan pool with a maximum 16 MiB charge, including its index
vector and inline pool header. Refusal, duplicate IDs and invalid IDs return the
untouched analysis for eager emission, without replacing a published plan.
Removing a plan releases its charge; the caller owns any returned temporary.
The pool is not yet wired into JIT preparation or execution.

The charge bounds pool-owned requested payload, not allocator rounding, transient
full analysis, code/tables/pending edges or process RSS. Test-only full liveness
oracles are excluded from retained-buffer charges; inline test headers are still
counted. No retained BTree node estimate remains. Later publication metadata
requires its own bounded ownership before enabling demand execution.

Run all 352 bytecode controls in both profiles, including exact budget admission,
one-byte-short refusal, immutable duplicate handling, release/reuse and eager
fallback words. Reconstruct both adopted captures exactly and repeat the saved
storage inventory, requiring every inventory to equal its plan charge. No guest
benchmark or demand adoption follows from this qualification alone.
