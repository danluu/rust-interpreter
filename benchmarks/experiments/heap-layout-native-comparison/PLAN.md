# Exact native equality with proven scalar-entry relocation

The original raw-byte gate incorrectly required equal ASLR addresses. Preserve
profile02's failed assertion and its one guest execution. This new verifier does
not mask arbitrary constants: each allowed MOVZ/MOVK x16 sequence must be directly
before blr x16 inside an operation-mapped original Call, target exactly the mapped
scalar entry for that Call's callee, and equal the canonical emitter sequence for
that process's recorded arena_base+entry_offset. Relocation identities and all
remaining instruction bits must match. Maps differ only in PID/base/code digest.
The existing independently qualified native observer first validates both dumps.

Nine controls include wrong targets/registers/opcodes/branches, noncanonical
immediates, duplicate/out-of-bounds entries, crossing span boundaries, changed
callees/maps and bad digests. Then verify saved original block execution, requiring
exact original assertions, per-PC counts, memory/entropy and native map ownership.
No guest, compiler, native publication, performance measurement or runtime changes.
Use shared lock45s/12GiB initial/8GiB child and source-bound independent closure.
Only a separately qualified continuation may then run the two missing guests.
