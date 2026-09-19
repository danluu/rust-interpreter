# Reserve the exact cost of a fixed native path

The closed budget-credit02 diagnostic parks check-only sharing: just1/2 eligible
CMP/B.LO samples. The remaining budget words still execute at every region.
This is a different mechanism: predebit a fixed path once, then execute its
intermediate regions without another budget sequence. No runtime code yet.

Select only forward **single-successor** edges between exact ordinary native
regions, with no range preflight at the destination. Calls, returns, branches
with multiple distinct successors, backedges and unsupported gaps cut chains.
Total reservation is capped at4096 original bytecode operations; cut an edge
if extending through it exceeds the cap. Every entry retains a checked path.
Only a certified direct native link may enter after its reservation sequence.
Unlike the previous DAG model, every reserved suffix has a single fixed path.

On checked entry, guard and subtract the entire chain credit. At an intermediate
region, the already reserved current cost is charged implicitly. Its statically
known pending suffix is credit[region]-cost[region]. Refund that suffix before
every early native fault or VM exit; when continuing through the certified edge,
carry it without modifying the physical budget. At a chain end it is zero.
Native Calls/Returns and all external/reentry paths see a canonical budget.

Qualify both virtual operation prefixes and physical cursor accounting. A native
fault refunds the unentered suffix but retains the original current-region debit.
The existing native engine precharges its whole current region before a fault;
the abstract semantic single-step remaining value therefore need not equal its
fault cursor. Record and check that distinction explicitly. When the larger
guard fails, use the existing VM tail without reservation. Its observable error
order and state must match the single-step oracle; it can have a different native
counter partition from the baseline. No argument relies on executing later ops
after a fault or on ignoring extents/cursor validation.

Model every short budget, fault position, entry point, artificial VM boundary,
loop, multi-successor cut, guarded target, opaque gap and capacity cut. Use an
independent step oracle and all512 three-node graphs plus seeded longer walks.
The diagnostic is not an AArch64 ABI, relocation or native-fault proof.

Join exact existing four-word budget spans to potential fast targets. Partition
samples into cost materialization, compare, branch and debit. Report all four
words as potential coverage, retaining entry-path uncertainty; do not call them
eliminated samples. Count logical region visits and possible fast-edge flow in
the separately bound complete profiles. No hot-path extra immediate is needed
by this abstract fixed-chain design; refund instructions occur on early exits.
Static code growth, compilation costs and cold/fallback behavior remain unmodeled.

Reuse the closed budget-credit02 source/evidence chain and unchanged exact native
decoder/graph reader.12controls, no guest/build/code publication. Shared lock45s,
12GiB admission and8GiB case floors. Freeze source through independent closure;
preserve failures. Production implementation still needs typed discovery with
unchanged range-planning order, audited fault refunds, exact entry relocation,
both-profile VM/ABI/budget tests and real changed-source primary/full guards.
