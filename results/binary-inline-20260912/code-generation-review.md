# Integer helper inlining code generation

Line references below name the baseline
`.work/perf-general-20260912/complete-scalar-inline-disassembly.log` and candidate
`binary-inline-disassembly.log` in the isolated worktree. Exact hashes and command
receipts are in [qualification.json](qualification.json). This review is of the
pure unprofiled `execute_impl` specialization.

Baseline lines 9933–9943 (`0x100009ff0–0x10000a018`) set a hidden result pointer,
call `binary`, and reload a discriminator, two value words and an overflow byte.
The helper writes those fields at lines 45402–45404 (`0x10002c94c–0x10002c954`).
Candidate lines 10866–10879 (`0x10000ae84–0x10000aeb8`) retain destination bounds
checks, mask register-held results and store value/overflow directly into guest
registers. The integer-helper result-buffer reloads and discriminator disappear.
XOR at lines 10659–10662 and AND/OR at 10688–10695 branch to that writeback with
no helper calls or arithmetic scratch-buffer traffic.

`float::binary` remains at candidate line 10107. Integer division/remainder
still call `___divti3`, `___udivti3`, `___umodti3` and `___modti3` at lines 10491,
10740, 10844 and 10852. Comparison/arithmetic paths reload frame/function
pointers at lines 10864–10865 (`0x10000ae7c/80`); division reloads them at
10854–10855. These are interpreter-state reloads, not result metadata.
Register count stays in `x21`; the baseline instead kept function pointer in
`x25`.

The pure symbol's padded span grows 12,288 → 14,656 bytes (+19.27%), or
12,276 → 14,624 excluding trailing padding. Both prologues save 96 bytes;
additional stack allocation falls from `0x470` to `0x460`, reducing the fixed
frame from 1,232 to 1,216 bytes. The old binary helper's separate 48-byte frame
also disappears on common operations. The executable grows from 1,082,960 to
1,099,424 bytes (+16,464).

An independent read-only review confirmed this mechanism and binary identity.
These observations establish no build-time effect or benchmark percentage by
themselves.
