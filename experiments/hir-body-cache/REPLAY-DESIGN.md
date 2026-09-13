# Next boundary: prevalidated body materialization and effect replay

Design only, against typed capture checkpoint `2e60d5fb` and exact compiler
`58e1e1f5311f4424ea81def4763081f6da62d9b3`. No replay implementation or workload
is added by this document. The historical journal checkpoint's actual compiler
check remains separate: its first attempt failed on three borrowed-key API
errors, now corrected in the prepared-value checkpoint. That failed result
cannot qualify this new codec or a future replay implementation.

The later capture-side `prepared.rs` checkpoint implements an owned typed-value
conversion prerequisite: it revalidates the supplied tree against the exact
current input, checks current S/E/prefix/local/resolution bindings, and prepares
actual pinned enum/ID/numeric values and checked absolute span recipes without
HIR/symbol/span interning. Its private `PreparedBody` token is intentionally
weaker than the `ReadyHit` below. The next source checkpoint borrows its exact
current input and adds a private cold-only materialization/recapture audit.
That audit receives only arena/span facilities after owner/E/source/context
checks and returns no HIR. It provides no exclusive context, vacancy/effect
replay or hit commit. Both saved and cold evidence must pass typed conversion;
every invocation still lowers stock. Cold arena roundtrip correctness remains
unrun and does not establish hit semantics or useful performance.

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
conservative guard. Exact state is required; a length check is insufficient.

## Crate features and ambient-state audit

The journal/tree checkpoint `2e60d5fb` omitted active crate features. The new
`entry.rs` capture-key component addresses that part of this audit; a complete
future replay entry proof remains outstanding. `Options::dep_tracking_hash(false)`
covers command-line settings, but active
`#![feature(...)]` values come from current crate attributes and are fed into
`features_query` separately (interface/passes.rs1020; expand/config.rs47).
The versioned normalized feature/array entry record now contains:

- Language features from `tcx.features().enabled_lang_features()`: sorted
  `(gate_name.as_str(), stable_since.map(as_str))` records, preserving duplicates.
- Library features from `enabled_lib_features()`: sorted gate-name strings,
  preserving duplicates. Both categories matter; do not serialize only language
  feature methods or the handful of features seen in the current fixture.
- Check the union of names equals the current `enabled_features()` set. The
  pinned private set is maintained as that union (feature/unstable.rs47–100).
  Unknown future state requires a source-policy decision, not silent omission.
- Each of the eight named `LoweringContext::allow_*` arrays: its **ordered symbol
  names**, including repetitions, tagged by field name. `allow_gen_future` is
  selected by `async_fn_track_caller` in `LoweringContext::new` (lib.rs347–369).
  Existing in-process Arc identity checks do not provide this persistent input.

Feature attribute spans are deliberately excluded from these boolean-input
records: no admitted skipped body branch reads feature-declaration locations,
and all feature-declaration diagnostics still run on current source. Feature
`stable_since` is retained as stable text. If the grammar later admits a path
that emits such a diagnostic, this narrower normalization is insufficient.

Do not obtain the snapshot by calling every boolean feature getter:
`Features::enabled` invokes `TRACK_FEATURE` when true (feature/unstable.rs114),
which records a `QuerySideEffect::CheckFeature` dependency (interface/callbacks.rs55).
The list/set accessors do not. Keep the ordinary `LoweringContext::new` call,
its `async_fn_track_caller` read and all normal frontend feature checks. A future
skipped feature read needs its normal dependency/side-effect replay in addition
to a correct key; fingerprinting alone does not replay that effect.

This is the bounded admitted-path audit on exact Cmono58:

| Read or branch | Current coverage / required condition |
| --- | --- |
| `tcx.features()` inside body helpers | The body-local type branch for `impl_trait_in_bindings` (block.rs84), explicit generic/return-notation branches (path.rs293/528), move/match/range/coroutine branches (expr.rs305/746/887/1425/1597) are excluded. Preserve those exclusions; capture acceptance is not proof for widening them. |
| `lower_qpath` async trait mapping/allowed features | Requires the whole value path to resolve to `Res::Def(Trait)` (path.rs49/75), which the gate excludes. No qself, bound modifier, unresolved projection or explicit generic argument is admitted. Path-segment lifetime lookup returns `None` by the gate (path.rs421–433). |
| Call metadata/attributes | The bare external call's legacy-const-generics metadata read is excluded. Local calls return before it (lib.rs406–437). Method lookup remains later ordinary type checking. |
| Body attributes, tools, AttrId and delayed lints | Body attributes are empty; `lower_attrs_with_extra` returns before `AttributeParser` (lib.rs1188). Paren attrs are also excluded. Attribute alias sources must be empty. Constructor/tool registration, enclosing attributes and all earlier/later lint work remain ordinary. |
| Edition and spans | `Options.edition` is tracked (session/options.rs417). The gate requires root hygiene and exact current owner source/resolution. Use current SourceMap/parent lowering; remap options are included by `dep_tracking_hash(false)`. Do not replace this with a token-only key. |
| Environment/configuration | No direct runtime environment read occurs in the admitted stock helpers. Expansion, cfg stripping, includes and environment macros run normally; their actual resolved AST is keyed. `unstable_features` and `-Zallow-features` are tracked; retain the existing forced-version rejection. An unknown future env read requires explicit invalidation/fallback. |
| Literal conversion / block safety / bindings | Successful literal conversion is determined by the exact token kind/text/suffix, with no ambient read; invalid literals cannot be stored. User unsafe/default blocks, raw/reference borrows and simple binding modes map directly. Source/AST errors still run normally. |

Command-line `lint_opts` and `lint_cap` are `TRACKED_NO_CRATE_HASH`, which
`dep_tracking_hash(false)` includes (session/options.rs43/348). Crate/module
`allow`/`deny`/`expect` attributes are **not** covered by that hash. This subset
never consults lint levels while lowering the body and creates no delayed-lint
callback, so those scopes need not be encoded into a body replay key. Their
current HIR attributes and all ordinary lint queries/checks must remain live.
Do not ask a HIR-dependent lint-level query from inside AST lowering just to
manufacture a scope fingerprint. `index_ast` forces early lints before stealing
AST/resolver inputs (lib.rs583–587); interface/passes.rs1133/1225/1245 retains
delayed-lint emission, late lint checking and expectation checking afterward.

Additional controls, all with byte-identical function bodies (crate-feature,
crate-lint and CLI variants now prepared in run-make; module variant planned):

1. Cold/repeated anchor, then add/remove crate `#![feature(async_fn_track_caller)]`;
   require the normalized language-feature key and allowed-feature-array input
   to change and the first run in each feature state to miss. Compare ordinary
   raw diagnostics in each state. Repeat with `#![feature(iter_next_chunk)]`,
   a pinned library feature (library/core/src/iter/traits/iterator.rs111), to
   exercise the separate library list; restore the original source afterward.
2. On an unchanged `fn anchor() -> u32 { let unused = 1; 0 }`, change crate or
   enclosing-module `#![allow(unused_variables)]` to `#![deny(unused_variables)]`
   and back. A reused body is permitted, but compilation must now emit exactly
   the ordinary current-scope lint error; no cached success/diagnostic is valid.
   Capture stderr without the optional cache-info logs. Also switch `-A` to
   `-D unused_variables` to require the existing session-option key to miss.

These invalidation/presentation controls are unrun. The capture record now binds
features/allow arrays; it does not yet provide the complete `ReadyHit` contract.

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
