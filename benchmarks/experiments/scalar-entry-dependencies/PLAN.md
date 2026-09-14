# Bound entry-address dependency obligations before execution

The strict captured-pointer-plus-offset census passes but covers only 43 of
1,561 adopted generated block samples. Defer that narrow runtime alone. A broader
static rule may reach the sparse-set/vector update closures rejected for loaded
or computed addresses. This diagnostic changes no emitter or native policy.

For each external address, collect its full SSA dependency DAG: captured inputs,
constants, arithmetic, casts, selects, packs and checked external reads. Preserve
all value bits and exact operation semantics; no numeric pointer inference.
Reject base/frame roots, phis, effects, forward dependencies or bounded-work
failure. Every captured read must have its own full range checked before loading.
All external ranges and write permissions must be preflighted before execution.
The existing no-failure-after-write rule remains a necessary condition.

A captured read may be hoisted only if every external write that can precede
that read in the original CFG is disjoint from its complete read range. Compute
those potential predecessor write sets with a monotone full-CFG worklist and
respect computation order within each original PC. Later writes are irrelevant
to the immutability of an already captured SSA value. Dynamic disjointness checks
are obligations, not performed by this classifier; numeric range overlap alone
is not pointer provenance or a complete memory guard.

Caps: 16 stores, 128 distinct ranges, 128 captured reads, 4,096 entry nodes,
65,536 dependency visits, 1 million order visits, 2,048 possible alias pairs,
and existing scalar shape limits. The prospective execution must evaluate the
sorted entry nodes, decline invalid/overlapping guards before any effects,
then preserve every original memory effect in order. Never replay committed
stores. Full memory/fault/budget/ABI modeling precedes any native wiring.

Run all thirteen controls per debug/release profile, including the prior seven
and six new controls for temporal alias obligations, computed addresses, bounds,
closed roots and an independent 32-diamond write-set oracle. Then reconstruct
all 245 exact archived bodies and report strict/simple and dependency eligibility
separately. Any broader sample join uses exact artifact identity and the closed
adopted captures. Counts are necessary-condition scope, not runtime admission,
instruction savings or a timing measurement.

Use scalar-entry-dependency-census-01, ROOT's existing shared target, shared lock,
two Cargo workers/test threads, max(14 GiB,8 GiB+twice allocated target) admission
and 8 GiB child floor. Freeze and close all commands including failures. No guests
or executable code are published. The restored store-log prototype stays parked.
