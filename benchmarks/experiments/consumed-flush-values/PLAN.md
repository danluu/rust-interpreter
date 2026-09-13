# Measure stores of values whose last use already completed

Start from the adopted runtime plus qualified test-only scratch/protocol observers.
No scratch optimization, native-boundary bundle or new runtime default is enabled.
Current exact samples assign135/180 samples to register flushing. The existing
flush predicate retains live-before OR live-after values at the last region PC.
A non-branch region has already executed that PC before flushing. Its operands
may therefore have no future reads, while their known values are still spilled.

First add only test-only span labels around the actual existing per-value flush
emission. Keep machine words, allocation, liveness, cache order, entries, budgets,
faults and code publication unchanged. Record analysis availability, exact region
end, fact kind, register and live-before/live-after. Count as eligible only values
with complete CFG liveness, a consumed non-branch tail, live-before and no live-after.
Branch/Switch operands and unexecuted tree-call tails remain excluded. Missing or
bounded-out liveness is never evidence that a register is dead. Joins, backedges,
entry initialization and VM fallbacks retain their current rules.

Three new controls cover final Store operands, unexecuted branch operands, and
values read by a following Call. Existing whole-CFG and budget controls remain
mandatory. Reconstruct both already saved unprofiled captures with observation
on/off and partition every actual flush byte, then reweight exact typed spans by
saved profiles and original self-PC samples. No new guest run or speedup claim.
Only sufficient coverage warrants an implementation and composition screen.

Use the shared lock with45-second admission, two Cargo workers,12 GiB initial
build admission and8 GiB per-child floors. Preserve the shared target, sources,
raw evidence, peer work, independent cleaner and paused goal. No repeated stages.
