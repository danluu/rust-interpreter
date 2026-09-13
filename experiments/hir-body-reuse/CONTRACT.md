# Body input diagnostic v2: source-only contract

Policy `hir-body-input-coverage-v2`; separate from unchanged whole-owner v1.
Compiler source: `58e1e1f5311f4424ea81def4763081f6da62d9b3`. This contract,
closed grammar and fixture are uncompiled/unrun. No cache implementation,
coverage increase or speedup is established. The next deliverable is a diagnostic
walker, not a compiler cache build. It must evaluate this actual gate, not regexes
or a hypothetical subtraction from v1 rejection counts.

## Exact intended cache boundary

Keep `lower_item` / `lower_trait_item` / `lower_impl_item`, attributes and
`lower_maybe_coroutine_body` stock. For an ordinary explicit noncoroutine body
with no contract, enter `lower_fn_body` normally; lower all parameters and their
attributes/patterns normally. The cacheable closure is only the ensuing call to
`lower_block_expr(body)`, before `record_body`. Both ordinary and cache paths
then call stock `record_body` and restore `lower_body`'s task/coroutine state.

The free/provided-trait/impl function routes all lower their bodies before their
signatures (`item.rs:323–340,1000–1022,1216–1236`). All generic/signature/header
lowering, AttrIds, diagnostics, delayed lints, `lower_define_opaque` and HIR
owner indexing/hashing still run in that exact order. Required trait methods,
foreign items, closures, async/gen functions and delegation are not this hook.
Outer `#[inline]`, docs, lint attributes and `#[test]` are never cached away.

## Entry/exit IDs and effects

Let **S** be `curr_owner.item_local_id_counter` immediately after normal
parameter lowering, not a guessed constant or a parameter count. Record every
current parameter binding's AST ordinal → actual HirId; include `self` and
binding modes. Let **E** be the counter immediately after `lower_block_expr`.
Every cached body-owned HirId must be represented as S-relative, in `[S,E)`;
references to parameters use the separately bound current prefix IDs. Preserve
empty statements and parenthesized expressions' actual lack of HIR nodes; block
expression wrappers use synthetic IDs after their blocks (`lib.rs:2594`).

Before a hit mutates anything, validate the entire wire tree and ordered event
journal against the current input, S, current binding map and supported state.
The journal distinguishes `LowerNode(ast_ordinal)` from `NextSyntheticId`, then
binding-map inserts. Replay through equivalent stock `lower_node_id` behavior:
current `children[DefId]=NonOwner(HirId)`, complete trait-map entries, and debug
relowering assertions must agree. It is insufficient to set only the final
counter. Preserve `ident_and_label_to_local_id` for the later signature path.
Return an expression, leave stock `record_body` outside the cache, and require
counter E after reconstruction.

V2's first subset requires no newly created definitions and no cached-body
attribute or delayed-lint effects. Compare `next_node_id`, newly created
`node_id_to_def_id`, children/attrs/lints/body-list additions and other mutable
lowering state before/after cold capture; unknown deltas reject storage.
Required scalar state includes owner, current item, loop/try/condition scopes,
contract state, coroutine/task state, dyn-type state, move-binding state and
partial-resolution overrides. Delegation overrides and nondefault unsupported
contexts reject before mutation. Parameter/signature effects remain ordinary;
nonempty *whole-owner* lifetime/definition maps are therefore not a rejection.
Entries attached to visited body nodes remain checked individually.

## Exact body input and external definitions

Key the compiler/session/codec policy via normal incremental compatibility, the
owner/context and stable source identity, exact expanded body and parameter
binding inputs, source bytes, all consumed spans, AST-node ordinals, partial
resolutions (including unresolved-segment counts), current definition identities,
and complete ordered trait candidates/import chains/ambiguity flags. Resolve
DefPathHashes to current DefIds; never persist raw NodeId/DefId/HirId values.
Absence and an explicitly empty trait-candidate entry are different inputs.

Keep parsing, expansion and all resolution running. Associated `self` is a
current local parameter binding. Method names alone are not resolutions: retain
all current trait candidates and let ordinary type checking select the method.
For initial v2, no explicit generic path arguments, QSelf or unresolved path
projections are supported. This still admits `self.field`, `self.method(args)`,
fully resolved nongeneric local paths and calls through local values.

Bare external direct-path calls invoke `legacy_const_generic_args` during stock
lowering (`lib.rs:406–435`, `expr.rs:214`). They are **pending**, not eligible,
until an actual current external-metadata proof establishes no legacy rewrite.
The future diagnostic can collect needed DefIds under the resolver borrow,
drop both borrows, query only external attributes using stock APIs, then borrow
again and evaluate the unchanged gate with that proof. Local direct calls need
no such query. Reject legacy-rewrite callees; no global query is bypassed.
Never call local HIR/analysis queries while resolver/AST Steal guards are held.

## Closed first grammar and spans

`policy.json` is the exhaustive starting grammar; all other forms fall back.
It admits simple local/self field/method/call bodies without new definitions,
not arbitrary Rust bodies. Body-local let patterns are only wild/identifier
bindings, without annotations; parameter patterns are initially the same even
though they are lowered normally. Loops, matches, closures, const blocks,
`?`, ranges, format/asm, struct literals, casts and explicit body type syntax
remain excluded until their codec/effects are added deliberately.

All body and referenced parameter spans must be DUMMY or root-hygiene spans
within the same current owner source extent; non-DUMMY spans use exact relative
byte ranges. Span diagnostics must retain real source identity and valid UTF-8
boundaries. On materialization, apply the current owner parent exactly as stock
`SpanLowerer` does. Reject macro-generated nonroot contexts and lowering paths
that create desugaring expansion IDs. No textual-source-only equality, span
stripping, invented parent IDs or unchanged-DefPathHash assumption suffices.

## Diagnostic acceptance and next gate

The after-expansion diagnostic has no actual LoweringContext S/E. Report
`structural_body_input_eligible`, pending external proofs, and exact per-owner
fallbacks; explicitly set `cache_effects_qualified=false` and `hir_ids_observed=false`.
Read-only borrowed-AST counts cannot establish the capture/journal invariant.
Retain normal compilation through analysis and full diagnostics as v1 does.
Count free, provided trait, inherent impl and trait impl roles separately;
retain all denominators, source/encoded bytes, per-map disjuncts and input hashes.

Before any development coverage, the real diagnostic must pass original/edit/
Unicode/restoration, local/trait-resolution changes and uncalled type/borrow/
const/panic controls with identical raw diagnostics to public rustc. Fixtures
must demonstrate positive free and associated-body eligibility and negative
external-legacy, lifetime-producing, nested-owner and hygiene cases. A subsequent
cache patch still needs real cold/hit/replay/storage-failure histories; no counts
from this source-only contract can satisfy that gate or the latency target.
