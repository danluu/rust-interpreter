# Spill only values live on ordinary-region successors

The exact adopted-code flush census identifies120/1,651 and165/1,439 generated
samples in values dead after a region exit. Most are terminal branch operands;
the initial consumed-nonbranch-only hypothesis covered just8/8 samples. Existing
facts survive flushing, so exit() can read its terminal operand without a second
copy in the private VM register array. This prospective mechanism changes the
predicate, not branch evaluation, and is not a speedup claim.

For ordinary/resumable regions with complete CFG liveness, flush only live-after
facts. Keep the facts and cache ownership untouched. The original scratch writes
used by flushing never overwrite x5/x6 or persistent pairs. Every successor read,
including an interpreter fallback or loop backedge, remains live and spills.
An exhausted/missing liveness analysis uses the unchanged conservative fallback.
The separate complete native-call-tree path retains its live-before-or-after
predicate because its tail may be an unexecuted Call using array-backed operands.
No guest memory store, initialization, budget, fault, strict type/borrow check,
artifact format, runtime option or16 MiB default changes. Do not include the
parked scratch forwarding or rejected wider boundary-copy/clearing bundle.

A test-only baseline switch reconstructs adopted behavior; normal tests enable
the candidate. Historical ignored observers explicitly choose their old baseline.
New tests require actual removed branch spills and unchanged live-successor spans,
then compare full-width branch selection (including duplicate cases), far register
numbers, cache pressure, joins, native/VM Calls and every instruction budget. Run
with/without persistent allocation, zero/full code capacity, ordinary/resumable/
tree/stub modes, and profiled/unprofiled execution. Existing CFG/backedge, memory,
strict-error and original application assertions remain mandatory.

An offline actual-emitter comparison must reconstruct both adopted captures exactly,
prove every removed word belongs to a dead-after flush value, retain all other
span lengths/PC identities and all assertion identities, and publish no code.
Then qualify the installed complete tool and exact workload profiles before a
fresh40-command primary changed-source screen. Stop if primary fails. A passing
screen alone permits fresh full histories with all five gates; it never adopts.

Use the benchmark lock (45-second admission), two Cargo workers,16 GiB initial
build admission and8 GiB child floors. Preserve all source pins, controls, raw
receipts, snapshots, peer work, independent cleaner and paused goal. No completed
stage repeats; admit larger cache histories separately using current headroom.
