# HIR body-v2: typed cold capture and materialization audit

This is an **uncompiled, unrun capture checkpoint**, generated against compiler
`58e1e1f5311f4424ea81def4763081f6da62d9b3`. The compiler checkout was read only.
The patch contains a closed typed body wire codec, actual cold HIR capture,
effect journal, tree/reference validator, current typed-value preparation and
a private cold materialization audit. **No hit path or effect replay exists.**
Every invocation executes stock body lowering and ordinary checks; the
reconstructed audit body is never returned or indexed.
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
No warning policy was relaxed. Its 22 unit controls remain unrun.

`capture-body-journals.patch` adds `-Zhir-body-cache-capture`, default off and
tracked by the normal incremental option hash. It prepares inputs for ordinary
free, provided-trait and implementation functions using the exact qualified
gate input (SHA256 `6df8b5b4fe1c0c88f6c21acbbf0514a61b48173bd037456b7563755c50ca15d1`).
The six top-level gate declarations have narrower module visibility; walker
logic and original gate bytes remain checked. The appended adapter invokes that same private walker and byte-compares its
encoded input before exposing the current AST ordinal table. The qualified
diagnostic, earlier patches and retained coverage evidence are unchanged.

## Actual compiler boundary

The hook wraps `lower_block_expr(body)` inside `lower_fn_body_block`. Ordinary
parameter/pattern/attribute lowering finishes first; capture observes the real
counter S, executes stock body lowering, then observes exclusive E. Stock
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
closure for a cold stock-lowered result; they do not replace ordinary lowering
or type checking as the semantic producer. They are not yet a hit admission API.

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
fields are converted explicitly. Saved records require preparation and discard
the token. The cold path additionally consumes its token through the private
audit below. It is not `ReadyHit`: no exclusive context, effect/vacancy preflight
or hit commit exists. No public API converts a token to HIR.

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

## Persistence and remaining work

Typed records use a fresh `hir-body-capture-v2-cold-materialization-1` namespace inside rustc's
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
feature/array part of the future entry proof, not a `ReadyHit` contract.

Even a valid saved tree is compared only **after another stock lowering**.
Logs say `same-tree-and-journal-after-stock-lowering` and
`cache_hits=0 body_codec=1 prepared_values=1 cold_materialization_audit=1 hit_materializer=0`. These fields identify
the implemented capture checks, not cache-hit or eligibility counts. Typed captures do not establish hits,
replay correctness, useful effect/output coverage or a speed improvement.

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
unit and native controls are unrun.

Still required: normalized persistent entry-state proof, exclusive current-context
preflight/commit, actual cold-audit correctness qualification, prevalidated effect replay through
ordinary allocation/binding/trait/child/debug semantics, then actual
cold/hit/edit/error/restoration/corruption/relocation qualification. The current
capture comparison does not substitute for any of those controls. External
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
