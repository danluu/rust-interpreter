# Scalar values in local native registers

The first scalar Call runtime passed all correctness controls but failed its
40-command edited-source primary (wall1.003720, CPU0.996103, A/A wall3.0585%).
Keep that failure closed. Its saved VM-stage median improves36ms, insufficient
for complete-command admission. This is a new runtime-only candidate.

Assign narrow computed SSA values to x3/x15/x16/x17 only when every use stays
in the definition block. x3 is free after the entry budget check; the scalar
body calls no helper. No ABI-preserved register or platform x18 changes.
Cross-block values, phis and values wider than64bits retain stack slots. Phi
input uses occur at predecessor exits. Live intervals follow emitted computation
order, distinguishing reads from result writes within one original PC.
A complete value may spill during allocation; code emits only after assignment
is final. Cap use analysis at250,000 per function and decline to ordinary JIT
on excess. Keep all admission, private failure and commit semantics unchanged.

First run seventeen scalar body/bridge differential tests per debug/release
profile, including three new pressure/phi/nonmonotonic CFG controls comparing
allocated native code with both old spilled native code and the scalar oracle.
Then qualify the workspace, strict/cache controls and exact original-test
profiles before the unchanged prospective40-command primary. Only a passing
primary admits the full five-project comparison and complete parser guard.
No repeat of the old candidate, source edits to tests, or threshold relaxation.

Use the same source-root Cargo target, two workers and the shared benchmark
lock. Initial build admission is max(14GiB,8GiB+2*allocated target bytes),
with8GiB child floor. Preserve setup time, exact source/binary keys and failures.
