# Exact-gate development coverage and the next boundary

The completed native development check in `results/hir-owner-development-coverage-01`
accepted one function in each nu-protocol configuration: 1/155 ordinary free
functions (1/12,488 all resolver owners), and 1/1,015 test free functions
(1/17,877 owners). The two ordinary builds and one test build account for all
three accepted records across the command. No output capture or cache hit was
measured. The existing scalar whole-owner cache does not justify a compiler
build for this workload.

The first combined owner-map guard rejected 96 ordinary and 345 test free
functions. That is not an estimate of how many would pass any widened codec.
The diagnostic records only the first failing source line; it does not identify
which disjunct on that line failed. No additional gate experiment was run.

All source references below are to unchanged compiler
`58e1e1f5311f4424ea81def4763081f6da62d9b3`.

| Guarded input | Actual scope and required preservation |
| --- | --- |
| `owner.id` | Consistency identity. Each `PerOwnerResolverData` belongs to one AST owner; this is not a mistaken whole-crate emptiness check (`middle/resolve.rs:196–218`). |
| `node_id_to_def_id` | Already-resolver-created, nonowner definitions; owner itself is excluded. `lower_node_id` feeds these into `OwnerInfo.children` as `NonOwner(HirId)` (`ast_lowering/lib.rs:945–951`). Current DefIds and exact local-ID assignment must be reconstructed. Newly lowering-created definitions are a separate `create_def` problem. |
| `trait_map` | Per-expression candidates for field access and method calls; even empty candidate slices get entries (`resolve/late.rs:5448–5478`). `lower_node_id` copies them into the HIR local-ID map. Preserve each ordered candidate's current DefId, complete ordered import-ID chain and `lint_ambiguous` (`hir/hir.rs:4740`). Names alone lose resolution and unused-import/ambiguity diagnostics. |
| `label_res_map` | Jump-to-loop/block NodeId mapping. Can be keyed by owner-local AST ordinals and rebuilt with current HirIds when the expression codec supports those constructs (`ast_lowering/expr.rs:1516`). |
| `lifetimes_res_map` / `extra_lifetime_params_map` | `LifetimeRes::Param` carries a definition; `Fresh` and `ElidedAnchor` carry binding/node structure. Some entries explicitly require lowering to create lifetime parameters (`ast_lowering/lib.rs:1077–1086,1116`). They are not generically free of side effects. |
| `import_res` | Resolution of the import owner itself; `lower_import_res` checks owner identity (`ast_lowering/lib.rs:996`). Removing its check does not add a plain free-function case. |

Normal resolution must continue. Its trait lookup also updates unused-trait
imports and glob information (`resolve/lib.rs:2190–2210`). Those effects already
occur before the proposed hook; replaying current per-owner HIR maps must not
replace or omit resolution. `into_owner_info` hashes the resulting trait map
and children (`ast_lowering/lib.rs:250–260`), including distinctions that look
irrelevant to expression evaluation.

The attribute/token/hygiene guard rejected another 41 ordinary and 647 test
free functions. These are combined first-site counts, not an attribute-only
measurement. Reusing a serialized empty attribute result would be wrong:
`lower_attrs_vec` creates delayed lint closures, and general normal attributes
retain current AttrIds (`ast_lowering/lib.rs:1213–1240`,
`attr_parsing/interface.rs:457`). Parsed doc comments have a simpler path, but
allowing them alone would not make the current scalar codec broadly useful.

A concrete general redesign is a **body reuse boundary**, inside the normal
`lower_fn_body_block` / `lower_fn_body` path (`item.rs:1367–1394`), instead of
serializing an entire `OwnerInfo` and suppressing all its lowering work:

1. Run ordinary item attributes, parameter attributes/pattern setup, signature,
   generics and header lowering in their existing order on every invocation.
   Keep their current AttrIds, delayed lints, definitions and diagnostics.
2. Reuse only a fully validated, supported noncoroutine body expression tree.
   Key every expanded/resolved input consumed by that subtree, owner/context,
   current input spans, parameter bindings and entry lowering state. Resolve
   nonlocal DefPathHashes to current DefIds; encode/replay exact current trait
   candidates and old-to-current node/HirId associations. Keep full fallback for
   nested owners, new definitions, unsupported spans and diagnostic-producing
   desugarings until those effects have an explicit representation.
3. Restore the exact local-ID counter and body/local-map effects before ordinary
   lowering continues. Body lowering precedes signature/generic lowering
   (`item.rs:323–340`), so a wrong counter corrupts subsequent signature IDs.
   `lower_body`'s task/coroutine save/restore and `record_body` must still run
   (`item.rs:1331–1353`). No arena mutation or diagnostic may precede a failed
   cache validation.

This is a redesign, not a safe deletion of the present guards. Its codec would
need ordinary calls, paths, field/method access and control flow to have a
plausible useful surface. Plain calls must retain the legacy const-generic
query/desugaring decision (`expr.rs:214`, `lib.rs:406`) or reject such callees
using an explicit current query result in the key. Signature and body effects
cannot be assumed independent merely because both appear in one source item.

A future diagnostic should report each owner-map disjunct and the exact proposed
body gate before another compiler build. It must preserve the current successful
raw evidence and remain development coverage, with no inferred speedup or
holdout claim. No redesign implementation or additional experiment is included
in these findings.
