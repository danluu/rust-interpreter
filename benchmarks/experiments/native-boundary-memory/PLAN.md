# Compose native boundary memory improvements

Start from the adopted guarded-local-facts VM, with qualified test-only protocol
labels. Current exact native-PC attribution puts 110/100 block/exhaustive samples
in frame clearing and 19/101 in argument/result copies. Opcode matching identifies
34/39 samples in the 64-byte clear loop and 13/89 in ABI byte-at-a-time loops.
The current flush categories also contain 135/180 generated samples. These are
partial samples, not expected gains. Implement one compatible bundle:

1. Keep every frame byte initialized, in its original order before argument
   copies. Use caller-clobbered SIMD zero stores for exact fixed ranges of at
   least 64 bytes, preserving scalar tails, and wider batches for large
   prechecked ranges. Never overrun the exact end. Preserve x16 callee targets,
   x17 register cursors, x22 instruction budgets and the host ABI. Independently
   check new instruction encodings with the local assembler. No signal faults,
   skipped argument slots, or read-before-write assumptions.
2. For ABI copies above 128 bytes, replace byte loops with the existing
   directional pair-copy machinery over the already checked complete ranges.
   Load each complete chunk before storing it, retain forward/backward overlap
   behavior and exact tails. Audit all tree and resumable callers for the helper's
   scratch-register contract. Keep original argument order and late failures.
3. Port only the qualified paired private-register transfer helper and its
   tests from 4b6c8b59; do not apply that historical commit's baseline reversions.
   Pair indices 0..31 and >=2048, keep scalar accesses in between, preserve both
   64-bit halves, and use the shared helper for persistent reloads. Its earlier
   -0.71% primary result was inside A/A and is not standalone adoption evidence.

Use exact-byte/canary tests across lengths, all alignments, both overlap
directions, identical pointers, register-offset boundaries, dirty reused frames,
unusual frame alignment, zero-sized operations, instruction-budget tails and
late argument/result faults. Run bytecode/workspace checks as appropriate in
debug/release. Keep the candidate source and complete tool immutable thereafter.
Qualify strict uncalled errors, original public/private tests, wrong edits and
restoration with the existing source pins. Preserve successful commands if a
controller fails; do not rerun them solely to repair reporting.

Before full timing, run one fresh primary-first 40-command changed-source token
screen with frozen A/A and baseline/candidate schedules. No tiny component timing
runs. If the screen fails, retain the result and leave the full study unstarted.
If it passes, use fresh full histories and require all five adoption guards.
No benchmark selector, assertion, checking, code-capacity default or compiler
option changes belong to this runtime bundle. LLVM remains only a host/native
control toolchain, never a guest backend.

Serialize substantial work with the canonical lock, 45-second admission,
two Cargo workers, conservative initial disk reservation and an 8 GiB child
floor. Preserve the shared owned build target, historical artifacts, peer work,
the independent cleaner and paused goal. No subagents or service activation.
