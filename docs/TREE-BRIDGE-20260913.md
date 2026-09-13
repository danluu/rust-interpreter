# Bounded trees inside the resumable JIT

The experimental bridge passes 556 workspace controls in debug and release,
but fails its 40-command changed-source performance screen and is not adopted. The
runtime remains on `experiment/resumable-tree-bridge-20260913`; main receives
these records and the design, preserving the other session's runtime/compiler
changes. The [build receipt](../results/tree-bridge-build-01/summary.json) binds
VM `7728eb39` and tool `1435ff79` to source `6b392b33` and the adopted exporter.

`--jit-tree-bridge` requires resumable calls. Before ordinary function emission,
the JIT prepares complete bounded direct-call dependencies. Trees whose ordinary
bodies have guarded ranges, and their ancestors, are excluded. A global quota
allows duplicate tree code to use at most one quarter of the requested arena;
the default remains 16 MiB. Stronger instruction, frame, register and memory
guards decline into the ordinary Call without guest progress.

The adapter preserves root clearing and ordered argument copies. Complete trees
avoid routine descriptor publication and return-table dispatch. On failure they
reconstruct active descriptors from their bounded host frames, recording only
successfully entered calls. The adapter publishes actual call/return counts and
passes normal `Boundary::finish` validation. It never bypasses type or borrow
checking. Separate tree profiles retain exact instruction ownership.

The controls cover arithmetic bounds, complete adapter/child ABI, nested faults,
all short instruction budgets, code/depth/working-memory limits, ordered aliases,
large registers, prepared-state isolation and option identity. The first six
focused runs include three compile failures, all retained. Their
[archive](../results/tree-bridge-focused-closure-01/summary.json) binds 1,202 source
inputs and contains 222 exact Git source blobs plus terminal receipts.

The [strict controls](../results/tree-bridge-qualification-01/summary.json) pass
119 commands; launcher qualification passes 386 tests with 16 declared skips.
All three [original profiles](../results/tree-bridge-profile-01/assessment.md)
preserve exact logical instruction counts, memory peaks and entropy. Block and
exhaustive execute 25.97M / 26.49M outer bridges, with 5.68M / 25.89M nested tree
Calls. Code occupies 12.19 / 14.80 million bytes, including duplicate
tree bodies. These instrumented counts do not establish speedups.

The [primary screen](../results/tree-bridge-screen-token-01/assessment.md)
retains all 40 commands and original assertions, wrong edits and restoration.
Median paired wall ratio is 0.995499 (0.45% improvement), inside 9.9249% A/A
variation. CPU ratio is 1.021747 (2.17% regression). Both required margins fail.
This does not establish a useful gain or prove zero benefit. Full primary,
held-out campaigns and repeated screens remain unstarted.

The [closure](../results/tree-bridge-screen-token-01/closure.json) verifies
1,958 frozen inputs, 56 retained artifacts and 380 Git source bindings. Setup
cost is separately recorded as 117.71 seconds for this qualified tool build.
Next examine the cursor and budget adaptation paid by the many small trees;
choose a materially different implementation before another performance test.
