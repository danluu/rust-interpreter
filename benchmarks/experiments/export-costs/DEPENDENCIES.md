# Observe compiler dependency reuse without skipping any lowering

Typed templates repeat 454ms (99.02%) of token's earlier function work and
90ms (87.61%) on folded. Before implementing reuse, test whether the pinned
compiler can track the template's semantic inputs across actual edits.

Add an explicit diagnostic flag requiring strict checking, function-cost
observation and an enabled incremental dependency graph. Use rustc's public
`MonoItem::codegen_dep_node` for each concrete instance and `DepGraph::with_task`
to observe queries consumed by its preparation/lowering. This metadata-only
exporter already rejects native code generation, so another backend will not
compile these mono-item nodes in the same compiler invocation. Record the
stable node fingerprint and whether `try_mark_green` accepts its prior inputs.

On both red and green nodes, execute the complete original lowering operation.
On green nodes, retain rustc's existing dependency edges and run verification
under `with_ignore`; do not allocate the same node twice. Continue recording
typed bindings and exact output hashes. No cache payload is loaded, no body is
skipped, no checking becomes lazy, and no interpreter/JIT behavior changes.

First qualify a small owned incremental fixture across original, local-body,
layout, constant, signature, generic, restoration and invalid-source states.
Compare ordinary/observed artifacts and original assertions. Check cold nodes
are new, stable nodes can be green, and any green node's actual typed template
agrees with the prior template for that fingerprint. Keep a false-green result
visible; graph-local IDs and shared exporter memo tables are not automatically
covered by rustc query edges. No such result authorizes caching.

Then use one token/folded history if the small control supports it. Compare
node keys and actual templates against the immediately preceding successful
compiler export, including a wrong guest edit whose strict compilation passed.
Use earlier unannotated weights only when output identities match. Record the
cost of green checks separately. This measures a possible dependency boundary,
not a cache hit rate or an end-to-end saving. Actual reuse additionally needs
current-session recipes for compiler constants/caller locations, function
references, vtables, statics/TLS and preserved allocation alias relations.

Pinned API evidence is the installed rustc source at revision
`cea272fa356e94bd2ee2cadf376630aa0683867a`: `rustc_middle/src/mono.rs`,
`dep_graph/graph.rs`, `dep_graph/dep_node.rs`, and `ty/context.rs`.
Preserve the compiler's metadata/incremental finalization and normal source
restoration. All work remains serialized under the existing benchmark lock.
