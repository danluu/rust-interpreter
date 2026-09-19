# Local-copy equality scope before production implementation

The closed adopted loop census finds178 cyclic Copy samples in the block capture,
with hot work concentrated in ordinary functions containing calls. Test whether
byte identities retained independently of virtual-register residency can prove
some copies redundant. This also checks ordinary acyclic regions, so report both.

Read existing closed maps, rendered operation identities and assigned PC samples
from adopted-hot-loop-census-02. No compiler, guest, timer or executable memory.
Native regions reset all state. At most4096 local byte identities and128-byte
copies are modeled. Copy sources snapshot before overlapping destinations change.
Unknown writes/calls/unreviewed operations clear state; known writes invalidate
overlapping bytes. Fresh unknown bytes never compare equal by accident. Capacity
exhaustion discards facts. Only exact Local, Imm and bounded64-bit Add/Sub address
idioms establish local ranges, within the active frame. Register definitions kill
old pointer facts. Zero copies give no modeled opportunity.

This is a scope model, not a production proof: rendered bytecode is not an
optimization interface. A later typed pass must use the actual emitter's frame
facts and preserve memory/budget/fault/exit semantics. Report modeled opportunity
PCs joined to existing samples, not eliminated instructions or time. Separately
report fixed-entropy whole-test logical counts. No workload names drive admission.

Before analysis, run14 controls: round trips, unknown data, memmove overlap,
partial/disjoint/unknown writes, bounded eviction, self copies, fresh regions,
invalid ranges, redefinition, effect barriers, exact arithmetic and15000 seeded
concrete-memory operations as an independent redundancy oracle.

Bind all inherited closed inputs and new sources. Shared lock45s,12GiB admission,
8GiB child/case checks. Freeze sources through independent closure, which verifies
archived Git hashes, terminal/logs/control count and recomputes all rows. Preserve
any failure; do not add a performance run unless useful scope and typed proof
justify it. No current Rust build is admitted by the disk reserve.
