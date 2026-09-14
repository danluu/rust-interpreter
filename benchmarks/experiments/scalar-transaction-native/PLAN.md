# Bounded native store transactions

The model's 369 passing bytecode controls/profile and exact saved-artifact census
retain 138 block samples. Extend direct AArch64 emission on this experiment
branch. Main stays on the adopted VM until complete qualification and the
changed-source primary gate pass.

Each reachable external store captures a checked stable host address, logical
address and up to 16 value bytes in a private stack slot. A zero host address
marks an unexecuted store. Check the pre-Call linear prefix, heap range, null,
width and read-only prefix at the original effect. No guest writes occur before
successful Return. At Return, commit active slots in topological effect order,
then return success to the existing bridge, whose remaining actions cannot fail.
The bridge commits its result after the external stores. No host callbacks.

Reads use proven low-address identities to omit disjoint prior stores and
forward from containing stores. A same-block preceding store that fully covers
the read also proves its range; its saved value can replace the backing read.
Unknown identities use runtime address checks. Exact-address containing stores
can forward; uncertain partial overlap declines privately and replays the whole
Call. The model remains the byte-exact oracle for all overlapping cases.

Keep the original <=512-operation/frame/register limits, <=16 store sites,
acyclic CFG, strict validation, shared work/code/stack budgets and x9-x14 scratch
restriction. Store slots retain values independently of scalar register reuse.
Standalone emission and ordinary production admission remain closed initially;
only a scoped test hook selects the new emitter and proof.

Compare full VM memory, values, original PC counts, budget/error tails, branches,
alias declines, register lifetimes, heap-free ABI and reconstruction. Preserve
all failed revisions. After native controls pass, re-census actual emission,
then qualify immutable tools, original profiles and the 40-command primary.
No larger histories follow a failed primary. Shared lock, two workers, protected
ROOT target and conservative disk floors remain mandatory.

Native controls03 and native census01 are now closed. The runtime experiment
selects the same backend through the existing explicit scalar-call option. The
old confined/read-only policy remains available only as a scoped test reference.
Full immutable workspace/strict/profile qualification is required for this
admission change before any latency screen. Main remains on df4006e0.
