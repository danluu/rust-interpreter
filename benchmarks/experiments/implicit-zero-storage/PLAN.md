# Implicit-zero storage runtime trial

The closed narrow-register-storage census admits this bounded experiment.
See docs/IMPLICIT-ZERO-REGISTER-DESIGN-20260918.md for the complete contract.

Only resumable native functions are eligible. Retain at most8MiB of boolean
proof entries per JIT, in addition to the existing per-function proof limits.
Publish proofs with successful code publication; declines retain the ordinary
representation. Diagnostic re-emission uses the exact retained proof even if
later functions exhaust metadata admission. Ordinary native/tree modes allocate no proof table and keep their current
representation, as do scalar bodies. All initialization remains.

Nine focused controls exercise dirty high backing at small/large offsets,
actual persistent-pair reloads and the host ABI, read/write aliases and uncommon
read roles, metadata/code admission, exact re-emission after admission fills,
wide/narrow callee reuse, skipped initial definitions, all budget prefixes,
original-PC profiles, interpreter reentry, intentional assertion faults, TLS
callback reuse and valid/invalid indirect handles.
The arithmetic control independently evaluates19binary operations,5widths,
2signedness choices and64operand pairs through actual VM arithmetic.

Run focused debug/release controls under the root lock, then review remaining
coverage before full workspace qualification. Keep strict checking and the
adopted compiler/exporter. No primary timing until focused/full correctness,
strict-cache tests and original profiles qualify the installed candidate.
The existing40-command primary, five-project full guards and both parser
histories keep their original gates. No gain or adoption is presumed.

Use acquire_lock(...,45), two Cargo/test workers, the existing owned target,
and max(14GiB,8GiB+2*allocated target) admission; check8GiB before every child.
Preserve the paused goal, all peer work and closed successful evidence.

Focused03 strengthens wide-to-narrow reuse: an actual interpreted128-bit
multiply forces the earlier wide value into backing before the frame is reused.
A native-only store could keep that value in a persistent pair and leave the
intended dirty byte pattern untested. The existing isolated native probes also
verify physically poisoned slots directly. Focused02 remains closed and valid
for its original fixtures;03 adds this guarantee and avoids proof-table allocation
outside resumable mode.
