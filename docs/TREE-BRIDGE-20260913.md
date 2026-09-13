# Bounded trees inside the resumable JIT

The experimental bridge passes 556 workspace controls in debug and release.
It has not been timed on changed-source workloads and is not adopted. The
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

Next: finish strict/cache/Cargo controls; replay the three original test profiles
with bound entropy; measure actual bridge coverage, compilation and duplicate
code; qualify launcher and screen protocols; then run the preregistered
40-command changed-source primary. Only a passing screen proceeds to full
primary and held-out projects. The census percentages describe static eligible
calls, not savings or measured bridge coverage.
