# Qualify the complete aggregate native Call bridge

The private ABI passes six native controls and 367 bytecode tests/profile at
d0a836a1. Now select the new confined zeroed-frame proof only when frame >512 or
result >16 bytes. Retain frame <=1024, result <=64, registers/operations <=512,
64 captured arguments of the original supported widths, the shared code arena,
and existing structural/native bounds. Debit up to one million scalar work units
for each memory-admitted wider attempt, including an early lowering decline.
Keep the old small-entry proof, allowance and initializer policy unchanged.

The bridge prechecks the whole result extent against the old logical memory
prefix and captures every argument there. It invokes one native body, then
commits ordered <=16-byte chunks from the private output. No fallible operation
follows success. A failed guard/body replays the ordinary Call. Preserve original
padding, future zeroing, logical addresses, exact instruction/profile counts,
peak memory, frame/register/working-memory limits and error order.

Run seven focused complete-VM controls in debug/release, followed by every
bytecode library test in both profiles (at least 374). The controls compare
ordinary interpretation and scalar-disabled JIT to the candidate, with profiles
and persistent registers independently on/off. Capture complete active linear
and heap bytes at success and error exits. Cover every result width, repeated
overlapping captures/results, odd tails, heap/readonly/overflow boundaries,
instruction and resource tails, private faults before an invalid Return,
new-frame input aliases, new padding destinations, escaped pointers and future
zeroing, zero-size invalid destinations, reconstruction, tiny arenas, explicit
eligibility and global-work exhaustion. Restore the prior test-only Memory Drop
snapshot observer independently of every parked runtime mechanism.

Freeze source and retain every command/outcome. Use the shared owned target,
global lock, two workers, no entropy shim, max(14 GiB, 8 GiB + twice allocated
target) build admission and 8 GiB child floor. Close pass or fail before source
edits. This is correctness qualification, with no original-project guest timing.
Workspace/launcher/strict/cache and original-profile qualification must precede
the already declared changed-source exhaustive primary. Main remains adopted.
