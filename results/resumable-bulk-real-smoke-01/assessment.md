# Original-artifact bulk initialization check

All four original executions (two artifacts × b2/new tool) finish successfully
with their assertions intact. Source `001065a` / tool `78e60cdd` uses resumable
Calls and persistent registers. The artifact hashes and instruction/allocation
limits match the preceding experiment. Instrumented instruction profiling is off.

Folded consumes exactly 4,138,403,285 logical instructions in both engines. The
candidate has 85,769 native entries, 25,913,904 native Calls and 25,916,861 native
Returns, identical to the preceding resumable tool. Code grows from 5,824,108 to
5,867,588 bytes. No function declines.

Token consumes 13,369,552,815 instructions in the candidate; the baseline consumes
13,369,497,496 because the original test uses randomness. The candidate executes
110,504,791 native Calls and 111,382,099 native Returns, with 22,417,899 entries.
Code grows from 14,608,884 to 14,722,684 bytes, within the unchanged 16 MiB budget,
with no declined functions. Returns may exceed native Calls because a frame
pushed by the VM can return natively.

The receipts preserve process identity, commands, binaries, artifact hashes,
outputs and frozen helper sources. Recorded saved-artifact times are diagnostics;
this is not a source-edit/build/test performance result. The original three-cycle
b2 comparison and its complete-command gates remain required.

[Commands and hashes](summary.json) · [Implementation plan](../../benchmarks/experiments/resumable-native-calls/BULK-CLEAR-NEXT.md)
