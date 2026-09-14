# Census virtual-zero scalar admission

The current Call/Return partition attributes 89/62 samples to ordinary frame
clearing. The scalar value graph already initializes every local byte and
register to zero, but its memory-plan prerequisite rejects reads before writes.
Count whether representing those zeros admits useful additional confined leaves.

Add only an explicit test-only memory-plan entry point. It may proceed after
`local_read_before_write`; retain the original initialization pass's work debit,
then require the full existing confined analysis and resolved frame accesses.
Do not relax other failures, shape/width/work bounds, external reads or writes,
nested calls, unsupported effects, scalar control flow or native emission limits.
The production memory-plan entry point keeps its current initialization rule.

Four focused controls per profile compare exact virtual zeros, padding,
conditional writes and instruction budgets against the reference interpreter,
check limits/effects, and retain scalar cycle rejection. There are 96 synthetic
reference comparisons per profile; no original-project guest is executed and
no native code is published. Offline native emission still has to succeed.

Scan the pinned token artifact once, retain every strict decline category and
each potentially relaxed function's memory/scalar/native outcome. Bound both
memory-plan scans by their recorded 256-million work budgets and retain counts
if a budget is exhausted. This structural census does not model runtime
preparation order or promise admission under the shared 16 MiB arena.

Join additional emitted candidates to the closed current Call/Return PCs via
the original program's exact call targets. Verify the complete prior fine
partition and report whole candidate transitions, frame-clearing samples and
other subparts separately. Those are coverage observations, not removable-time
estimates. Choose implementation only after the additional coverage is known.

Use the ROOT-only shared target, two Cargo workers, existing host profiles,
the global lock, max(14 GiB, 8 GiB + twice allocated target) initial admission
and an 8 GiB child floor. Preserve all attempted runs and other sessions' work.
