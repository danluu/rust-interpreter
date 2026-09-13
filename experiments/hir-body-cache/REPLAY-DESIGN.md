# Next boundary: prevalidated body materialization and effect replay

Design only, against typed capture checkpoint `2e60d5fb` and exact compiler
`58e1e1f5311f4424ea81def4763081f6da62d9b3`. No replay implementation or workload
is added by this document. The historical journal checkpoint's actual compiler
check remains a separate prerequisite; its result cannot qualify this new codec.

## Proposed API and miss boundary

Keep the current capture path unchanged. A separate tracked, default-off reuse
policy gets a fresh record namespace and source identity. Do not interpret old
capture-only sidecars as qualified reusable bodies.

The eventual API should have this shape (illustrative, not Rust implementation):

```text
prepare_hit(&mut LoweringContext, current Candidate, saved Payload)
    -> Result<ReadyHit<'context>, Miss>
ReadyHit::commit(self) -> hir::Expr
```

`ReadyHit` holds exclusive access to the same lowering context and an owned,
fully prepared tree/event plan. It cannot outlive that context or be applied to
another context. No public constructor or `CheckedTree -> Expr` shortcut exists.
Every `Miss` occurs before changing the context, allocating HIR or interning
symbols. Commit has no fallible decoding, lookups, parsing, queries or fallback.
Normal allocator failure remains process failure; this does not promise OOM
rollback. An internal postcondition failure must never retry stock lowering on
a partly advanced context.

Preparation executes at the existing boundary: ordinary parameter lowering has
finished, stock `record_body` and later signature/generic/owner work have not run.
It must first complete all of the following:

1. Exact current gate/key and storage checks, `Frame::enter`, `journal::check`,
   `Current::new`, and full tree/reference/order validation from the checkpoint.
   Keep the validated S, E and exact current prefix together. Check all absolute
   byte-offset additions and all `S + relative` IDs before constructing them.
2. Normalize entry compatibility as explicit predicates and stable inputs,
   replacing the cold frame's process-local pointer identities as a persistence
   proof. Static context guards stay identical; all current bindings must be
   exactly the ordinary parameter prefix. Current owner, source and resolver
   mappings are rebound from this invocation, never loaded as old IDs.
3. For every planned AST allocation, confirm `opt_local_def_id(node) == None`
   using both current maps (lib.rs862–869), not just the earlier gate. Require
   every future attribute/trait/debug target slot to be vacant and no current
   binding overwrite. Debug `can_relower` remains false. Existing owner entries
   outside the interval remain untouched. A newly supported definition requires
   a new child/definition replay contract; it must not slip through this one.
4. Bind the exact current trait candidate slice for each recorded allocation,
   including empty slices and full import/ambiguity data. The fresh resolver
   input already keys their stable identities; never rebuild a list from trait
   names. Retain ordinary parsing/expansion/resolution and their side effects.
5. Convert wire operator/type-suffix strings into their actual pinned enums and
   integer strings into `u128` now. Prepare every reference, identifier/literal
   byte payload and span recipe. No unchecked parser or `unwrap` on serialized
   data may remain in commit. Keep float spelling and C-string NUL bytes exact.

Entry compatibility need not hash entire unchanged attribute/body/child maps:
this closed body neither reads nor changes their existing entries. It does need
explicit vacancy/nonaliasing predicates for every replay destination. The cold
frame's pointer comparisons still check the implementation during capture;
they are not a cross-session key. Allowed-feature arrays must be covered by
tracked options or normalized by stable content, never by Arc pointer value.
Disambiguator/new-definition/override/impl-trait/lint/move state keeps its current
conservative guard. There is no permission here to weaken one to a length check.

## Commit effects and materialization

The event plan records concrete current AST NodeIds, current owner/parameter
HirIds and verified S-relative body IDs. Replay the validated event sequence
through the stock methods, rather than writing only the final counter/maps:

| Event | Stock operation | Preserved effects |
| --- | --- | --- |
| AST allocation | `lower_node_id(current_node)` (lib.rs940) | Counter, exact current trait slice, debug checker; child insertion ruled out by preflight |
| Synthetic allocation | `next_id()` (lib.rs962) | Counter only |
| Binding | Existing instrumented binding insertion | Exact NodeId-to-current-ID relation; no overwrite |

Assert returned IDs equal the prevalidated plan. All events can precede HIR
arena construction only if that construction is query/diagnostic/effect free:
for this closed grammar it reads only prepared values. Do not call ordinary
expression constructors that allocate additional IDs. Do not run the current
cold trace and a replay trace simultaneously.

The materializer exhaustively maps the wire tree to the same pinned HIR fields,
using prepared IDs/resolutions and arena allocations for slices/references.
For a relative span, make an unparented root-context span from the checked
current owner base and offsets, then call the **current** `SpanLowerer::lower`
(lib.rs388–403). Dummy uses `DUMMY_SP` followed by that same lowerer. Construct
identifiers with that span; preserve independent expression/literal/path/call/
operator spans. Never copy old `Span` intern indices or parent DefIds.

Each `Resolution::Input(ordinal)` uses its prepared current `Res`, and each local
uses its prepared current body/parameter HirId. No metadata query is needed to
rebase those references. External bare calls still fail the gate: the pinned
legacy-const-generic helper can query attributes for them (lib.rs406–437).
Ordinary local calls return before that query. Do not widen this exclusion while
implementing replay.

Finally check counter E and the expected binding/trait/debug delta as internal
postconditions, return the Expr, and let stock `record_body`, owner indexing,
hashing, delayed checking, type/borrow/const checking and codegen proceed.
Empty-body-attribute alias operations have no effect because preflight proves
all their source slots empty (lib.rs1242–1248). No diagnostics are synthesized,
suppressed or substituted.

## Small executable qualification required afterward

The first replay implementation should add only a prepared-value converter,
an exhaustive materializer and this commit adapter; keep the input grammar and
all fallbacks fixed. Before any workload coverage claim, compile the exact
patch and run cold/**actual hit**/edit/restoration controls with an asserted
positive hit counter. Reuse the fixture's ordinary raw diagnostic comparisons
and add corruption with valid-checksum malformed tree/reference cases, current
owner/parameter-ID relocation, Unicode source-prefix relocation and trait-input
invalidation. A rejected hit must leave the observed entry snapshot unchanged
before falling back to stock lowering. Successful hits must reproduce the cold
complete tree and effect journal, not merely the final native output.

Only after those controls may a fresh development coverage run measure actual
hit/output/effect acceptance. The earlier structural counts and current typed
cold captures establish none of that, and provide no latency or holdout claim.
