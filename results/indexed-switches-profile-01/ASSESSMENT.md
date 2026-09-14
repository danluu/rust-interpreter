The first original block replay passes assertions, exact logical/backend counts,
memory, entropy and code size, then stops at the new raw-byte equality check.
It emits 11,952,720 bytes in both captures, with 854 differing words. Initial
inspection locates differences in the imm x16 sequences used for scalar Calls;
the two processes have different executable-arena addresses.

Do not discard the check or rerun this completed guest. A bound relocation
comparison must validate both same-process maps, preserve identical spans and
body offsets, permit only the exact original Call's scalar callee address before
blr x16, and require every other word identical. Four negative/positive controls
cover wrong targets, unrelated mutations, missing calls and ambiguous ownership.
Attempt 02 will reuse this exact completed block capture and run only the two
remaining original tests after that comparison succeeds. No runtime changes.
