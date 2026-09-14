# Shared cursor for bounded trees

The custom JIT now has a second experimental bridge implementation. It passes
556 workspace tests per profile, 119 strict/cache commands, 19 focused ABI and
fault controls per profile, and all three exact original-workload profiles. Its
changed-source performance screen fails; the runtime is not adopted.

The [prior bridge](TREE-BRIDGE-20260913.md) failed its performance gate. Saved
profiles show that it paid two budget memory accesses and four instructions for
each of 180.36M / 381.02M tree regions. The new ABI keeps the resumable cursor in
x19 and remaining budget in x22, debiting the preproved region length with one
subtraction. The root adapter shares call/peak state and restores the caller's
profile pointer. Fault descriptors remain reconstructed and checked normally.
Bridge children also use the adopted frame/register clearing helpers.

The [build](../results/tree-shared-cursor-build-01/summary.json) binds VM
`2c20261d` in tool `a984e603` to source `50e2af88`, retaining the exact adopted
exporter and wrapper. Setup takes 106.84 seconds, excluding lock wait. Original
standalone tree tests and external host-register preservation still pass.

The [profiles](../results/tree-shared-cursor-profile-01/assessment.md) preserve
logical counts, memory and bound entropy. Actual bridge coverage is unchanged.
Code totals 12.14 / 14.75 / 2.07 million bytes with no compilation declines;
duplicate tree bodies remain below the quarter-arena quota. These diagnostics
do not establish an end-to-end gain. Keep the default 16 MiB, two workers,
original tests and all source/type/borrow checks.

The existing 40-command primary gate compares changed production source with
the adopted baseline, duplicate control, historical anchor and ordinary native
execution. Only a passing screen permits full primary and held-out comparisons.

The [40-command screen](../results/tree-shared-cursor-screen-token-01/assessment.md)
reports wall ratio 0.982971, inside 4.1545% A/A variation; CPU ratio is 0.998983.
The wall margin fails. Original assertions, wrong edits, exact artifacts and
restoration pass. The [closure](../results/tree-shared-cursor-screen-token-01/closure.json)
verifies 1,958 frozen inputs, 56 artifacts and 380 source bindings. No full,
held-out or repeated screen commands run. Inspect same-process native samples
before selecting another mechanism; instruction-count reductions are insufficient
performance evidence.
