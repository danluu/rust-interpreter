# Preserve the exact byte-comparison failure

Profile02 executed only the block assertion, returned0, and passed the exact
per-PC, guest-memory, entropy and map validation before the new raw-code equality
assertion failed. Preserve terminal1 and every generated profile/code/map/log hash,
binding the original frozen sources to their Git revision. Do not rerun this guest.

Read-only diagnosis found854 differing words in427 absolute scalar-call address
materializations; code sizes and maps match apart from PID, arena base and code
digest. The original emitter embeds arena_base+callee_offset before blr x16.
A separate, controlled relocation verifier must prove every allowed difference;
all other bytes remain exact. No conclusion or admission follows from this
diagnostic alone. No runtime source, threshold, guest input or entropy change.
