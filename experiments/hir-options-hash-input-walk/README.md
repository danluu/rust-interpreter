# Options-hash plus one input walk: proposed source composition

This is an uncompiled, unqualified source proposal. `proposed.patch` targets the
exact options-hash compiler revision `4de35bdacef0e3cd18a66bc30b5459c19e09b118` at
`/Users/danluu/dev/rust-interp-runtime-exporter-20260918/.work/hir-options-hash-compiler-01/source`. That source and both existing candidates are unchanged. No checkout,
compiler, test, probe, benchmark or holdout was used.

The input-walk candidate has three changed files. Its input.rs preimage matches
the current source exactly. Every semantic hunk matches at its exact original
line with no offset or fuzz. The current mod.rs differs from the old input-walk
base only at the cached options-hash call, outside the traversal hunk. The new
patch replaces only the two consecutive probe/current_nodes calls with the
single ProbedInput call. It preserves that cached call, all other current
mod.rs bytes, and the complete context.rs accessor/storage implementation.

The old input-walk source identity is deliberately not applied. The options
closure has 25 acyclic members plus source_identity.rs; input-walk's 24 members
are a subset, with context.rs as the sole additional member. Replacing input.rs
and the one mod.rs call regenerates the complete 25-member identity as
`4ae2790b6283fd3569035c15b7b031603781f96a2dc2eca7b8631525cff55680`. Exactly input.rs, mod.rs and source_identity.rs differ. The proposed
patch SHA is `1e4e47585965731581cfcb788c2a100e2bb7eb417a12131c81d0d85562b777ee`. `provenance.json` retains every original/current
input SHA and seven-field identity, every original hunk SHA, both complete
closure maps, exact before/after hashes, and the actually compiled base audit.

This proposal composes options-hash and input-walk only. The separate packed
sidecar source proposal is not included or silently selected. Any later
three-way composition must retain its own complete source/identity proof.

Before adoption, independently verify this proposal and create a separately
admitted isolated candidate. Qualify actual accepted/rejected ASTs against the
old two-walk oracle: normalized Input bytes and ordered NodeId/body flags,
escaped strings, byte/C strings, underscored numeric literals, local patterns,
resolutions/traits, hygiene, parent spans, duplicate nodes and depth/size bounds.
Do not use synthetic hand-written AST models as the sole equivalence proof.
Preserve first-pass interning and diagnostics; duplicate internal debug/trace
and allocation activity are intentionally reduced. Re-run inherited lowering,
interface, support, options-hash driver/run-make and unchanged/edit/restore,
corruption, current-tree/journal and intentional-failure controls on the actual
new compiler. The current options-hash compiler's successful tests are base
provenance and do not qualify this new patch.

Finish the current options-hash runtime and strict Ruff qualification first.
This follow-on reduces redundant body-cache preparation and comparison
serialization. It leaves other frontend work intact and provides no numeric
speedup, cache-off benefit, or complete latency-target claim.
