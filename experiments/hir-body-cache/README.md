# HIR body-v2: actual capture and journal boundary

This is an **uncompiled, unrun capture checkpoint**, generated against compiler
`58e1e1f5311f4424ea81def4763081f6da62d9b3`. The compiler checkout was read only.
It is the first part of the requested body-v2 cache implementation, not a
complete cache: no typed HIR body codec, body materializer or hit path exists.
Every invocation still executes stock body lowering and all ordinary checks.

`capture-body-journals.patch` adds `-Zhir-body-cache-capture`, default off and
tracked by the normal incremental option hash. It prepares inputs for ordinary
free, provided-trait and implementation functions, using the exact qualified
gate bytes (SHA256 `6df8b5b4fe1c0c88f6c21acbbf0514a61b48173bd037456b7563755c50ca15d1`).
The small appended adapter invokes that same private walker and byte-compares
its repeated encoded input before exposing its current AST-node ordinal table.
The qualified diagnostic, previous patches and retained evidence are unchanged.

## Actual compiler boundary

The hook wraps only `lower_block_expr(body)` called from `lower_fn_body_block`.
`lower_fn_body` first lowers all actual parameters, their patterns and attributes
normally. The checkpoint then observes the real `item_local_id_counter` as S;
stock lowering runs; the checkpoint observes E. `record_body`, signatures,
generics, outer attributes, owner indexing/hashing, all checking and native
codegen remain stock and in their original order.

Instrumentation records calls, not guessed counts:

- `lower_node_id`: current AST ordinal and actual S-relative allocation.
- `next_id`: actual synthetic allocation and relative ID.
- Pattern/label binding insertion: current ordinal, old binding and new ID.

The ordered journal therefore handles initializers before local/pattern IDs,
statement IDs after their expressions, separate method-segment IDs, and zero
allocation for parenthesized expressions, empty statements and trailing Expr
statement wrappers. Overwrites, unknown ordinals, unsupported new definitions,
new AST IDs, nested owner transitions and attribute parser activity invalidate
the capture. A counter change without a recorded allocation also fails.

## Validation and unchanged effects

`journal::check` is a fallible, mutation-free structural boundary. It validates
the actual prefix parameter bindings, contiguous S-relative allocations,
checked E arithmetic against the actual `ItemLocalId::INVALID` bound
(`0xFFFF_FF00`, with E exclusive), unique AST allocation, binding target/order/identity,
and trait-map presence, including an explicitly empty candidate list. It admits
unallocated AST ordinals because stock lowering legitimately drops some syntax.
It does **not** claim that an arbitrary journal describes a valid HIR tree.
The opaque `Checked` type has no conversion into HIR or arena allocation.

Cold exit validation compares the full observed binding map and full trait-map
delta against the journal, using exact current resolver candidate slices. It
preserves preexisting attrs, bodies, children and `define_opaque` by immutable
object identity within that compiler process; no pointers enter stored records.
It clones and compares the entire disambiguator state. The patch adds derived
`PartialEq`/`Eq` to its existing Clone type; it does not expose or mutate private
definition state. Debug builds also compare the complete relowering-checker map
against the actual recorded AST allocations.

The context snapshot exhaustively destructures the pinned context/owner state.
It rejects nonempty delayed-lint callbacks, impl-trait accumulators, generated
definition maps, partial resolution overrides or move-binding stacks at both
boundaries. This is an additional conservative gate, not an assumption that
the 482 previously reported normal `nu_protocol` bodies all pass. It binds
owner/current-item/arena/resolver identity, next AST ID, allowed-feature arrays,
contract/coroutine/task/try/loop/condition/dyn state. New fields require an explicit
source decision. Definitions and attribute-parser entry points also mark the
trace invalid, including changes whose outputs might otherwise disappear.

## Storage and comparisons

Journal evidence lives in the existing locked incremental session directory.
It uses a distinct policy/filename, a bounded fallible JSON decoder, exact input
key and checksum, and fresh-inode publication so previous hardlinked sessions
remain intact. Missing, malformed, mismatched, oversized or unwritable records
fall back to ordinary lowering. A record contains no raw NodeIds/DefIds/HirIds.

The key binds the exact qualified resolved input, tracked session options,
compiler cfg version, assertions configuration, policy, and a generated source
identity covering every changed hook and all gate/journal/storage source. This
reuses ordinary compiler incremental session selection and avoids hashing
compiler/library binaries on every process. Actual build/install provenance
must still freeze the generated patch and compiler normally.

Reading a valid old journal only permits a comparison **after another stock
lowering**. Logs explicitly say `same-journal-after-stock-lowering` and always
report `cache_hits=0 body_codec=0`; nothing is called a hit. The stored record
is evidence that a cold result passed this effect boundary, not reusable HIR.

## Prepared controls and remaining work

The patch contains five unit tests for S relocation/prefix and trait presence,
bad journal order/duplicates/gaps, invalid prefix/overflow, the actual ID
sentinel and exclusive-end boundary, and malformed/key/
checksum/oversized storage with old-hardlink preservation. Its run-make fixture
contains original/edit/restoration, local/self field/method/trait calls,
parameter bindings, shadowing, generic headers, empty/parenthesized syntax,
Unicode insertion before owners, and an actual trait-import edit. It compares
normal execution and exact raw compiler diagnostics for uncalled type, borrow,
const and constant-panic errors; damaged sidecars must still compile normally.
These tests are prepared source only. No pass count is claimed.

The next implementation boundary is deliberately explicit:

1. A closed typed HIR body wire tree matching every admitted expression,
   statement, path, literal, pattern and span field; unknown outputs reject.
2. A complete tree/reference validator proving every allocated ID occurs where
   stock HIR requires, including synthetic wrappers, shared local references,
   current parameter IDs, exact DefPathHash-to-current-DefId rebasing and the
   current span lowerer's parent/hygiene rules. Journal well-formedness alone is
   insufficient, and span relocation is currently exercised only by stock code.
3. Prevalidation of normalized entry state and the entire body/journal before
   any hit mutates a lowering context or arena; complete replay through stock
   allocation, binding, trait/child and debug-checker semantics.
4. Real cold/**actual hit**/edit/uncalled-error/restoration/corruption/relocation
   controls with the compiler built from the exact patch, followed by measured
   effect-gate coverage. The current same-journal control is not this hit test.

External direct calls remain rejected without current legacy-const-generic
metadata proof; generated hygiene, body-local type/lifetime/new-definition
syntax, attributes and the other v2 exclusions remain unchanged. Current
structural coverage cannot predict the stricter effect/output coverage or
timing benefit. No full compiler build, benchmark, holdout or adoption
qualification is authorized by this source checkpoint.

Regenerate the source patch without changing the compiler checkout:

```sh
python3 experiments/hir-body-cache/prepare_patch.py --source /path/to/exact/Cmono58
```

`patch.json` binds all original/replacement files, the generator and candidate
sources, qualified gate and final patch. Source generation and whitespace
inspection are the only checks performed for this checkpoint.
