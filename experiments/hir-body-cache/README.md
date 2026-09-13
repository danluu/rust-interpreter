# HIR body-v2: typed cold capture and journal boundary

This is an **uncompiled, unrun capture checkpoint**, generated against compiler
`58e1e1f5311f4424ea81def4763081f6da62d9b3`. The compiler checkout was read only.
The patch contains a closed typed body wire codec, actual cold HIR capture,
effect journal and tree/reference validator. **No body materializer or hit path
exists.** Every invocation executes stock body lowering and ordinary checks.
The earlier journal-only checkpoint remains immutable at `3f3e9c28`.

`capture-body-journals.patch` adds `-Zhir-body-cache-capture`, default off and
tracked by the normal incremental option hash. It prepares inputs for ordinary
free, provided-trait and implementation functions using the exact qualified
gate (SHA256 `6df8b5b4fe1c0c88f6c21acbbf0514a61b48173bd037456b7563755c50ca15d1`).
The appended adapter invokes that same private walker and byte-compares its
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

## Persistence and remaining work

Typed records use a fresh `hir-body-capture-v2-tree-1` namespace inside rustc's
existing locked incremental session, bounded fallible JSON decoding, an exact
input key/checksum and fresh-inode publication. Old hardlinked sessions remain
intact. Missing, corrupt, mismatched, oversized or unwritable records fall back.
The key includes the exact resolved input, tracked options, compiler cfg
version, assertions configuration and generated identity of the entire patch.
It uses ordinary incremental session compatibility, with immutable compiler
byte identity audited separately during build/install qualification.

Even a valid saved tree is compared only **after another stock lowering**.
Logs say `same-tree-and-journal-after-stock-lowering` and
`cache_hits=0 body_codec=1 materializer=0`. Typed captures do not establish hits,
replay correctness, useful effect/output coverage or a speed improvement.

Prepared source tests cover duplicate/missing/out-of-range/wrong-kind tree IDs,
journal/tree order disagreement, actual ID sentinel and prefix boundaries,
current parameter/local/nonlocal resolution binding, UTF-8 span boundaries,
typed literal domains, lowered assignment operator spelling, and malformed/
checksum/key/oversized storage with old-hardlink preservation. The run-make
fixture retains ordinary/edit/restoration, shadowing, fields/methods/traits,
generic headers, parenthesis/empty syntax, Unicode prefix relocation and raw
uncalled type/borrow/const/panic diagnostic controls. All are **unrun**.

Still required: normalized persistent entry-state proof, complete current-span
reconstruction and body materialization, prevalidated effect replay through
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
