# Bounded budget credit across forward native edges

Investigate a distinct mechanism after reviewing the full archived experiments.
The parked scalar-copy-budget candidate shortened each individual guard; x22
budget residency is already present. This proposal shares a larger precheck
across ordinary native regions while retaining each region's exact debit.
Neither the failed opcode rewrite nor another unchanged screen is included.

Start with an offline model and the two closed adopted native captures, not a
runtime patch. Construct nodes from exact emitted resumable ordinary regions.
Direct normal-return successors come from the closed branch parser. Calls,
Returns, unsupported gaps, backward/self edges and targets with a nonempty
range-guard span terminate credit propagation. No credit crosses a guest call.

Process nodes in decreasing original PC. A source may cover its own cost plus
the maximum credit of its strictly forward admitted successors, up to 4096
bytecode steps. If that bound would be exceeded, cut all prospective fast edges
from that source. This is a bounded DAG even when the guest CFG contains loops.
The edge certificate is credit[source] >= cost[source] + credit[target].

Every external entry, VM reentry, Call return and noncertified edge checks the
complete credit for its destination. A certified native edge may use a separate
entry that only materializes/subtracts that destination's original region cost.
It must not bypass memory range guards. An insufficient larger precheck declines
before progress and uses the existing exact interpreter tail; no instructions
are charged for an unexecuted branch. Every region retains its original debit,
per-PC identities and successful profile counts. A later runtime design must
audit short-budget reentry, all fault/cursor contracts, and code-map relocation.

Model qualification enumerates three-node graphs and short budgets, plus loops,
diamonds, multiple entries, call/guard barriers, capacity cuts, malformed inputs,
and deterministic longer paths. Compare operation/fault prefixes with a separate
single-step oracle. This does not prove native machine-code correctness.

Count samples at exact existing CMP/B.LO words only after recognizing the whole
four-word budget sequence and original cost. Report potential coverage at nodes
with incoming certified edges, not eliminated samples: the saved capture does
not record which entry was used. Keep whole-span samples separately. Also report
fixed-entropy native region visits and fast-edge flow bounds separately, retaining
the extra immediate needed on checked entries as an explicit cost. Those counts
are not retired instructions, elapsed savings or complete-command estimates.

Use at most65536 nodes and262144 edges per function. Twelve GiB analysis admission,
eight GiB per case, shared lock with45s admission; no Rust build, guest execution,
code publication or storage retirement. Hash-bind the complete closed capture
chain, model and controls; freeze through independent recomputation/closure.
An implementation still requires typed analysis, emitter/ABI/budget/fault tests,
original Rust suites and the unchanged source-edit primary/full project gates.
