# Checked scalar memory code generation

The immutable baseline is `same-frame-vm`; the candidate is
`complete-scalar-inline-vm`. Binary hashes and raw paths are recorded in
[qualification.json](qualification.json). The full candidate disassembly is
`.work/perf-general-20260912/complete-scalar-inline-disassembly.log` in the
isolated worktree; its command receipt is the adjacent `.json` file.

The pure, unprofiled `execute_impl` has no calls to `Memory::range`, `load` or
`store`. Common 1/2/4/8/16-byte success paths pass no scalar or range result
metadata through stack temporaries. The eight-byte load at disassembly line
10240 (`0x10000a4bc`) transfers the result through registers to the guest
register write at line 10255; the sixteen-byte load is at line 10377.
The eight-byte store at line 10288 (`0x10000a57c`) reaches dispatch at lines
10296–10297 without a result sentinel; the sixteen-byte store is at line 10390.
Generic-width scratch and copy calls remain at lines 10242–10249 and
10290–10295.

The interpreter symbol spans 10,496 → 12,288 bytes including alignment
(+17.07%), or 10,484 → 12,276 bytes without padding. The fixed VM stack grows
from 1,200 to 1,232 bytes; separate scalar helper frames disappear on common
paths. Completion at lines 10251 and 10296 reloads the frame pointer and
register count with `ldp x3, x4, [sp, #0x58]`; the baseline reloaded just the
frame pointer. That is loop-state traffic, rather than result metadata.
The executable grows by 32,480 bytes.

These observations were independently reviewed. They explain what changed in
code generation, but do not attribute a measured percentage to one mechanism.
