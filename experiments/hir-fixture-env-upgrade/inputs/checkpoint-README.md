# HIR body-v2: exclusive, verified body replay

This is an **uncompiled, unrun diagnostic successor** to fixture checkpoint
`75b5a567` and replay checkpoint `5cd6acd3`, generated against compiler
`58e1e1f5311f4424ea81def4763081f6da62d9b3`. The compiler checkout was read only.
The production guard, grammar, flags, replay implementation and 26 unit tests
are unchanged. This keeps the fixture environment repair and adds a suffix to
body-tree rejection reports identifying the first failed boundary: current
input, capture, validation, preparation, cold audit or post-audit exit. Every
check, its order, publication condition and ordinary-lowering fallback remain
unchanged. Reports still require `-Zincremental-info`.

The existing compiler's separate direct probe used its real version identity.
It compiled the unchanged fixture successfully but emitted 24 body-tree
rejections and no successful captures or hits. A subsequent HIR dump showed
the minimal literal function had the expected IDs and visible spans. The new
phase labels are diagnostic instrumentation, not a claimed fix or speedup.
[Direct probe evidence](../../results/hir-direct-capture-probe-01/README.md)
retains the original rejection reports and unchanged source/compiler guards.

The frozen predecessor passed its selected compiler check, all 26 unit tests,
stage1 compiler build, identity probes and tracked-option unit. Its native
run-make then failed the initial capture assertion without emitting any capture
or reuse reports; that failure remains in the
[original evidence](../../results/hir-native-correctness-failed-01/README.md).
Bootstrap's pinned `test.rs:2919` sets `RUSTC_FORCE_RUSTC_VERSION=compiletest`,
while production `prepare` intentionally rejects every present value. The
shared fixture constructor now removes that variable for ordinary, capture
and reuse histories. Production refusal of version overrides is preserved.
The original 203-member failure archive remains
`a5a6e0e5b2c49603baa0c4d6d2e51b40f57279ab5f4f4f82d75cad0240d3e58b`;
the new fixture has not run and does not reclassify that failure as a pass.

The patch contains a closed typed body wire codec, actual cold HIR capture,
effect journal, tree/reference validator, current typed-value preparation and
a private cold materialization audit, and a separately selected exclusive hit
preflight/commit adapter. Capture-only mode still always returns stock HIR.
Replay is default off; every experimental hit retains complete tree, journal
and post-state verification. No hit, performance benefit or replay correctness
has yet been observed for this source checkpoint. Normal parsing, expansion,
resolution, signature/parameter lowering, checking and codegen remain intact.
The earlier journal-only checkpoint remains immutable at `3f3e9c28`.
Its separate actual compiler check failed with three `E0308` errors in
`effects.rs`: the pinned unordered-map sorting API requires a borrowed key.
This checkpoint corrects all three projections, retaining numeric ordering
(including a stored numeric key for `NodeId`, which lacks `StableCompare`).
That historical failure does not qualify this new, still-uncompiled checkpoint.
The separate prepared-value checkpoint `33f4c4e4` then reached the compiler
without type errors but failed the unchanged warnings-as-errors policy: nineteen
unreachable public declarations, one private-interface warning and one unordered
feature-set iteration warning. This successor narrows the declared visibility
and obtains feature names through the stable declaration iterator, retaining
independent cardinality/membership equality against the actual enabled set.
No warning policy was relaxed. The warning-fixed cold checkpoint remains
separately frozen at `60d5be45`. Its selected compiler check and all 22 unit
controls passed with zero warnings/errors; its native cold run-make remains
unrun. Those results do not qualify this new replay implementation. This
checkpoint's 26 unit controls remain unrun.

`capture-body-journals.patch` adds `-Zhir-body-cache-capture` and
`-Zhir-body-cache-reuse`, both default off and tracked by the normal incremental
option hash. Reuse has its own namespace; if both are selected it takes
precedence, retaining the same cold capture/audit on misses. It prepares inputs for ordinary
free, provided-trait and implementation functions using the exact qualified
gate input (SHA256 `6df8b5b4fe1c0c88f6c21acbbf0514a61b48173bd037456b7563755c50ca15d1`).
The six top-level gate declarations have narrower module visibility; walker
logic and original gate bytes remain checked. The appended adapter invokes that same private walker and byte-compares its
encoded input before exposing the current AST ordinal table. The qualified
diagnostic, earlier patches and retained coverage evidence are unchanged.

## Actual compiler boundary

The hook wraps `lower_block_expr(body)` inside `lower_fn_body_block`. Ordinary
parameter/pattern/attribute lowering finishes first; capture observes the real
counter S, executes stock body lowering on misses, then observes exclusive E. Stock
`record_body`, signature/generic/outer-attribute work, owner indexing/hashing,
all checking and codegen retain their original order.

Instrumentation records actual `lower_node_id`/`next_id` allocations and
binding-map insertions. The journal accounts for separate method/path segments,
initializer-before-local IDs, Expr/Semi statement IDs after expressions, and
no allocation for parentheses, empty statements or trailing Expr wrappers.
Unknown ordinals, overwrites, definitions, new AST IDs, nested owners and
attribute parsing reject capture. Empty attributes retain their stock shortcut.

The entry/exit snapshot exhaustively binds context/owner fields, full
existing binding and trait maps, full disambiguator state, debug AST-ID map,
existing immutable attribute/body/child/opaque entries and scalar state.
Delayed lints, impl-trait accumulators, definition maps, resolution overrides
and move-binding stacks conservatively reject. No snapshot pointers enter disk.
The earlier effect journal's scope is unchanged.

## Typed fields and complete ID closure

`wire.rs` covers the current closed body grammar: arrays/tuples, typed literals,
paths, ordinary/local calls, methods, unary/binary/assignment operators, blocks,
if/return, field/index access and ordinary/raw borrows; simple bindings and
wildcards; ordinary let/Expr/Semi statements. Capture destructures every HIR
struct field explicitly. Unsupported variants or nondefault fields reject,
including generic argument payloads, delegation segments, body types,
let-else, generated unsafe blocks and destructuring-assignment locals/patterns.
Gate acceptance alone does not establish output eligibility.

The representation preserves binding modes and binding target separately,
actual infer-args flags, block rules, literal style/unescaped bytes/type suffix,
operator/call/bracket spans, independent literal versus expression spans, and
actual node/identifier/path spans. In particular parenthesized expressions can
widen the Expr span while leaving the literal span intact. HIR `AssignOp`
preserves this pinned compiler’s `AssignOpKind` spelling (`+=`). Ordinary
assignment's *lowering* order is LHS then RHS.

`journal::check` validates contiguous S-relative allocation, prefix bindings,
actual `ItemLocalId::INVALID` (`0xFFFF_FF00`) arithmetic with exclusive E,
binding events and trait presence. It intentionally permits omitted AST IDs.
`validate::check` additionally requires:

- Every allocated ID occurs exactly once in the owned wire tree with the
  appropriate current AST kind; the root matches the recorded root ID.
- Synthetic IDs occur only for the root and if-then block expression wrappers.
  All other nodes have their current AST origin. Unsupported desugaring falls
  back even if the structural input gate accepted its syntax.
- A second traversal reconstructs the stock allocation/binding event order
  and compares the complete journal, including initializer and statement order.
- Body binding IDs equal their actual pattern IDs. All local uses match the
  fresh resolver's binding target, map to an actual body or parameter binding,
  and body bindings precede their uses in the allocation sequence.
- Nonlocal resolutions point to the exact current input ordinal. The validator
  binds its current `Res`/DefId, whose kind and stable definition path are in
  the exact input key; no old DefId is decoded or guessed. Missing resolution
  is permitted only for stock path/method segments, including ordinary methods.
- Captured spans have root hygiene and the current owner parent. Relative byte
  offsets stay in the exact current owner source and at UTF-8 boundaries.
  Dummy spans remain distinguished. No old parent/hygiene IDs are serialized.

The opaque checked tree retains current resolution/binding proofs without
allocating HIR or interning symbols. These checks prove wire/tree/effect
closure for a cold stock-lowered result; they do not replace ordinary type
checking or prove that an arbitrary malicious payload is the lowering of its
source. A sidecar is trusted only under rustc's existing owned incremental
cache contract, exact input/source identity and fallible storage validation.
The full current-context preflight below is additionally required for a hit.

`prepared.rs` adds an opaque, owned `PreparedBody` token. Its sole constructor
repeats full tree/order/reference validation against the **exact supplied
current input**, rather than transferring a `CheckedTree` proof between
contexts. It checks S/E, the complete parameter/body binding map (including
unused bindings), current-owner identities and resolution/reference pairs.
The token now borrows its exact `Current` until consumed, preventing that input
from changing or escaping its lifetime. `Current::new` requires root hygiene and an owner span whose byte length
equals the exact UTF-8 source. Preparation checks source-base/length and every
absolute `BytePos` addition, including overflow and UTF-8 boundaries.

The token contains current `HirId`/`Res` values, actual pinned operator/binding/
borrow/block/type-suffix enums, parsed `u128` integers, exact float spelling and
owned string/byte data. Spans remain checked current-owner coordinate recipes;
no `Span`, `Symbol`, `ByteSymbol` or HIR node is interned or allocated. All wire
fields are converted explicitly. The cold path consumes its borrowed token
through the private audit below. Replay may detach only the owned `BodyValues`
after separately completing current-context preflight. The borrowed token is
not `ReadyHit`, and no public API directly converts it to HIR.

## Cold materialization audit

After stock lowering, the cold exit frame, tree and preparation checks, the
private `prepared_audit.rs` entry verifies current owner, S/exclusive E, exact
source range/bytes, expected wire tree, prefix and context association. The
actual current counter must equal E and tracing must already be disabled.
An ephemeral session/arena/resolver pointer tuple guards the immediate cold
call and never enters disk. The caller retains the lowering context, candidate
and borrowed current input lexically; pointer equality alone is not a lifetime
or exclusive-context proof.

The builder receives only `hir::Arena` and the current `SpanLowerer`. Its
exhaustive constructors preserve every admitted field and fixed absent field,
current IDs/resolutions, reference-versus-slice layout, operator spans,
independent expression/literal spans, exact float spelling and C-string NUL
bytes. Checked coordinate recipes use root hygiene and the ordinary span
lowerer; `DUMMY_SP` also receives the normal current-parent treatment. It has
no ID allocator, lowering map, resolver, query, fallible lookup or parser.
Arena allocation and symbol/span interning begin only after audit preflight.

The duplicate HIR is recaptured and fully revalidated against the same current
input, then compared to the complete cold wire tree. The caller repeats the
full exit-effect check afterward. Failure rejects capture and returns the
already-produced stock HIR; it never relowers an advanced context. Success
also returns stock HIR. No audit node is registered as an owner/body or passed
to compiler queries. Allocated duplicate nodes remain unused until arena
teardown; this diagnostic overhead is not a speed optimization or cache hit.

## Exclusive replay boundary

`prepared_replay.rs` has the only `ReadyHit` constructor. It borrows the actual
`LoweringContext` exclusively, retains the caller's live `Candidate`, and owns
the checked journal, typed body values, current ID event plan and expected exit
state. `Current` is a local preflight view, never a self-referential token field.
There is no unsafe code, lifetime extension or persistent pointer identity.

Before the first context mutation, preflight repeats the actual entry-key and
owner/session/arena/resolver association checks, fallible storage decoding,
journal/tree/reference/span validation and complete typed conversion. It
checks S and every prefix binding, full unchanged entry state, vacant body ID
ranges in attribute/body/trait maps, both current definition maps, binding and
debug-node insertion vacancies, and exact current trait-slice presence
(including empty slices). Full current trait candidates preserve ordered
DefIds, import IDs and ambiguous-import lint flags. Unsupported state or any
failure returns a miss; the caller asserts that the complete entry snapshot
is unchanged before stock lowering. No HIR, symbol or span is allocated during
preflight. Its allocations are ordinary owned validation data only.

Commit consumes that exclusive token, records actual calls to stock
`lower_node_id`, `next_id` and the existing binding adapter, and constructs HIR
using the same arena/current-span builder as the cold audit. Every returned ID
must equal its prevalidated current ID. There is no fallible return or stock
retry after the first effect. All definitions/children remain unchanged for
this closed subset; stock ID allocation copies current trait slices and runs
the debug relowering checker.

**Verification is always on in this first experimental replay policy.** The
actual replay Trace must equal the complete recorded journal. It is removed
before the materialized HIR is recaptured/revalidated and compared to the full
wire tree; complete bindings, trait contents, debug IDs, counter E and excluded
state must equal the precomputed exit. Candidate and trace must both be absent,
and no compiler error may have appeared. The closed commit calls no diagnostic
emitter. An invariant failure terminates compilation; it cannot fall back after
state advance. These audits add real work to every hit and cannot be removed
from a timing boundary. Any later audit removal requires its own qualified
source change.

Only then is the reconstructed HIR returned to ordinary `record_body`, owner
indexing/hashing, later checks and codegen. Hit logs include
`cache_hits=1 verify_tree=1 verify_journal=1 verify_poststate=1`; the prepared
native controls require these fields, exact ordinary output and raw diagnostic
equality. Source implementation and these assertions are not an executed hit.

## Persistence and remaining qualification

Capture records use `hir-body-capture-v2-cold-materialization-1`; replay records
use the separate `hir-body-reuse-v2-ready-hit-1` namespace inside rustc's
existing locked incremental session, bounded fallible JSON decoding, an exact
input key/checksum and fresh-inode publication. Old hardlinked sessions remain
intact. Missing, corrupt, mismatched, oversized or unwritable records fall back.
The key includes the exact resolved input, tracked options, compiler cfg
version, assertions configuration and generated identity of the entire patch.
It uses ordinary incremental session compatibility, with immutable compiler
byte identity audited separately during build/install qualification.

The final record key also binds `entry.rs`'s normalized **actual body-entry**
context, obtained after ordinary parameter lowering and `Frame::enter` rather
than from the earlier owner preparation. It sorts the language/library feature
lists while retaining categories, duplicates and language stabilization text,
checks their union against the actual enabled set, and preserves every ordered
symbol name in all eight named `allow_*` arrays. The public list/set accessors
avoid boolean getters and their `TRACK_FEATURE` side effects. Ordinary context
construction and feature/lint checks remain unchanged. Empty/oversized or
inconsistent normalized data rejects capture before reading a sidecar; the
complete key stays under the existing record budget. This implements the
feature/array part of the entry proof; exclusive state/vacancy checks remain
separate and mandatory.

In capture-only mode a saved tree is compared **after another stock lowering**.
Cold-path logs say `same-tree-and-journal-after-stock-lowering` and
`cache_hits=0 body_codec=1 prepared_values=1 cold_materialization_audit=1 hit_materializer=0`. These fields identify
the implemented capture checks, not cache-hit or eligibility counts. Replay
misses use that same cold producer and write only after its successful audits.
Typed captures do not establish replay correctness, useful effect/output
coverage or a speed improvement.

Prepared source tests cover duplicate/missing/out-of-range/wrong-kind tree IDs,
journal/tree order disagreement, actual ID sentinel and prefix boundaries,
current parameter/local/nonlocal resolution binding, UTF-8 span boundaries,
typed literal domains, pinned assignment operator spelling, feature-list category/
duplicate/version changes, allowed-array order/field association, union/key
boundaries, and malformed/
checksum/key/oversized storage with old-hardlink preservation. The run-make
fixture retains ordinary/edit/restoration, shadowing, fields/methods/traits,
generic headers, parenthesis/empty syntax, Unicode prefix relocation and raw
uncalled type/borrow/const/panic diagnostic controls. New run-make controls add
and remove language/library features around the same anchor, require first
new-feature states to be cold, and compare exact raw current diagnostics for
crate allow/deny and CLI `-A`/`-D` unused-variable settings. Native cold-state
controls do not isolate key-field causality; the pure normalization tests cover
those individual changes. All are **unrun**.

Four additional prepared-value controls cover current coordinate relocation,
UTF-8/exclusive-end/overflow boundaries, S/source/kind mismatches against an
earlier checked tree, complete unused-prefix/current-owner/resolution binding,
all pinned assignment/suffix enums and `u128` overflow. These are also unrun.
Two cold-audit controls add context/exit/source rejection and actual HIR arena
literal recapture equality, including dummy/current-parent treatment, UTF-8
relocation, independent spans, float spelling and byte/C-string preservation.
The native fixture also includes explicit value/unit returns, wildcard/unit
bindings, lazy binary conditions and unary/assignment combinations. All new
unit and native controls are unrun. Four new pure controls cover occupied
preflight ID ranges and exclusive sentinel E, non-overwriting binding/debug
reservations, complete trait import/lint/order/duplicate equality, and malformed
tree IDs/UTF-8 spans with freshly valid storage checksums. Native reuse histories require cold then verified hits for free and
associated bodies, shifted Unicode source, changed trait/import resolution,
uncalled type/borrow/const/panic failures activated by source edits with
unchanged cfg, restoration, corruption and feature/lint invalidation. Exact
per-name counts require both `field` bodies and both trait-implementation
`choose` bodies. Crate and enclosing-module allow→deny→allow controls require
actual hits on the unchanged anchor while current-scope raw errors match the
ordinary compiler. Separate CLI lint controls require first-state key misses.

New override controls reintroduce both an explicit empty value and a nonempty
`RUSTC_FORCE_RUSTC_VERSION` after the shared constructor. For each value,
ordinary/capture/reuse modes use distinct fresh positive and error incremental
directories, leaving every existing cold history intact. Positive info probes
require no capture/reuse logs and compare actual native outputs. An activated
uncalled type error must retain identical complete raw JSON diagnostics,
including `E0308`, across all three modes. All twelve fresh directories must
contain no HIR sidecars. These add twelve compiler commands and six native
executions; both the new controls and their regenerated patch are unrun.

Still required: actual compile/API validation, all 26 unit controls, ordinary
and capture-only native controls, then actual verified
cold/hit/edit/error/restoration/corruption/relocation qualification on this
exact source. Earlier capture comparisons do not substitute for replay
qualification. External
direct calls without a current legacy-const-generic proof remain excluded.

No compiler build, benchmark, holdout or adoption qualification has run for
this source checkpoint. Source generation, Python AST parsing, whitespace and
patch-applicability checks are recorded separately in `source-checks.json`.

```sh
python3 experiments/hir-body-cache/prepare_patch.py --source /path/to/exact/Cmono58
```

`patch.json` binds original/replacement files, generator/candidate inputs, the
unchanged qualified gate and final patch. Historical source/evidence remains
available at its original commits.
