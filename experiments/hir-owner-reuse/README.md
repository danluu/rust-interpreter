# Narrow owner-lowering feasibility spike

The later [opt-in compiler candidate](CANDIDATE.md) implements this seam as a
separate, uncompiled patch. This document preserves the original feasibility
snapshot; its two prototype files are not the candidate implementation.

Source-only against compiler `58e1e1f5311f4424ea81def4763081f6da62d9b3`.
Neither file is imported, compiled, executed, or installed. This is an acceptance/key
prototype plus a closed output representation, **not a working compiler cache**.
There are no coverage, performance or correctness measurements.

The seam is implementable with a compiler patch. `ItemLowerer::with_lctx`
(`rustc_ast_lowering/src/item.rs:57`) creates isolated owner state and passes its
result to `PerOwnerLoweringState::into_owner_info` (`lib.rs:209`). A hit could
populate that fresh state and return the reconstructed `OwnerNode`; the existing
finalizer would still calculate current hashes, index every HIR node, and report
invalid IDs. This avoids serializing `OwnerInfo` itself.

`resolved_input.rs` accepts only free, safe, ordinary Rust functions with primitive
scalar argument/return types, immutable binding or wildcard patterns, primitive
literals, local references, arithmetic, return, parentheses and ordinary blocks.
It rejects every other variant, all attributes/doc comments, retained token streams,
generics, where clauses, lifetime maps, trait maps, non-owner definitions, unresolved
or external resolutions, nested owners, non-root hygiene, parented input spans,
cross-file spans, large/deep owners and prior compiler errors. Rejection means the
unchanged stock path. An absent segment resolution is represented explicitly;
it is different from an explicit `Res::Err`, which is rejected.

The key contains the exact current owner's source text and every accepted AST field,
including visibility, names, literal spelling/suffix, optional-field presence,
positions, and `lifetime_elision_allowed`. Node IDs become deterministic traversal
slots; all current `partial_res_map` entries for those slots are compared, including
absence. A local resolution must point to an admitted binding in this owner.
The owner uses its current `DefPathHash`, never an old `LocalDefId`. An identical
identifier that now resolves to a different binding or a user type misses. Editing
an earlier owner can shift byte positions and raw IDs without invalidating an
otherwise equal input. The candidate does not compare a pre-expansion token hash.

These are all owner-specific resolver inputs for this subset: the remaining owner
maps are explicitly empty. The crate-wide resolver, early-lint buffer and per-parent
disambiguator are not cache payloads. Normal `index_ast` and
`LoweringContext::new` must execute on both paths, including their ordinary query
reads and the normal one-time disambiguator steal. `next_node_id` is unobservable
in this subset because no accepted branch allocates a new AST node or definition.

`owner_wire.rs` represents only the accepted function/tree, one body, scalar values,
owned strings, owner-local HIR indices and relative spans. Reconstruct `Symbol`s
by interning the saved strings; rebind **every** HIR ID and span parent to the current
owner. Every non-dummy span uses the current item's byte base and root context;
dummy spans remain dummy but receive the normal current owner parent. No old arena
pointer, raw `NodeId`, crate number, `DefIndex`, `AttrId` or expansion ID is reusable.
External `DefId` decoding is unnecessary because the input gate rejects all such
references. Supporting them later requires a different policy and dependency proof.

The concrete next patch is small in scope, but still needs these implementations:

1. Add a child module inside `rustc_ast_lowering`, invoking the probe only for
   `AstOwner::Item` functions. Keep `lower_to_hir` **eval_always** (`queries.rs:230`),
   `index_ast`, all parse/expand/resolve/early lint work and all subsequent HIR/type/
   borrow/const/MIR checking. An exporter provider override cannot call the private
   lowerer/finalizer or recover an AST once the original provider steals it.
2. Implement the two exhaustive HIR↔wire conversions, bounded byte decoding, exact
   canonical key equality after lookup, and fresh arena allocation. Check each
   defining local ID exactly once, each reference's kind/target, the body ID and
   local-ID limit; preserve empty statements/parentheses' actual lowering layout.
   Reject unexpected HIR variants, nonempty generic args, error nodes or nonlocal
   span parents. Do not deserialize arbitrary `OwnerInfo`, attributes or closures.
3. On a normal miss, assert before publication that generated-definition count is
   zero; `node_id_to_def_id`, overrides, children, attrs, trait map, delayed lints,
   opaque data and transient impl-trait accumulators are empty. Such a violation
   leaves the already-computed stock result in use and publishes nothing. It must
   never rerun a lowerer that already emitted side effects. The subset proof is
   primary; these are defensive checks, not a diagnostic-replay mechanism.
4. Restore only the body, tree and item-local counter into the fresh state, then
   run stock `into_owner_info`. Recompute derived hashes/index/parenting and keep
   normal downstream validators. Wrap storage in a new compiler-policy namespace
   bound to exact executable/options/session identity; misses, decoding failures,
   cache damage or unavailable storage always use normal lowering. Cache lookup,
   input validation and output allocation remain in the measured compiler command.

The static zero-effect argument comes from the accepted branches themselves:
empty attributes return immediately (`lib.rs:1190`); `Fn.eii_impl=None` generates
no extra attribute (`item.rs:163`); no generics or lifetime-map entries reach
`create_def`; primitive/local paths with no generic arguments cannot trigger
legacy const-call rewriting, trait-object/opaque lowering or lifetime insertion;
valid scalar literals take `lower_lit`'s non-diagnostic branch (`expr.rs:503`).
`lower_fn_header` selects its ordinary non-const Rust ABI branch. There is therefore
no delayed `FnOnce` lint or `AttrId` to replay for an admitted successful output.

Before enabling any hit, compile this spike, run shadow comparison against stock
lowering for its accepted forms, and exercise changed resolution, shifted/Unicode
spans, malformed cache, uncalled type/borrow/const errors and each rejection family.
Shadow comparison is qualification work, not a timing mode. The prototype has not
yet established that actual expanded ASTs commonly retain no token stream, that
the complete wire conversion passes HIR validation, or that validation plus decode
is cheaper than lowering. The first two are concrete next admission checks; the
third is the eventual performance question. This seam does not save macro expansion
or resolution and should not be represented as a route to 0.5 seconds by itself.
