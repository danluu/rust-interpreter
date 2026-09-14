# Simplify bounded native store logs

The parked store candidate passed correctness and exact original profiles but
failed its complete 40-command primary. The closed store-cost census
reconstructs 245 saved bodies exactly. In successful block-test paths it counts
32,936,960 write checks covered by prior same-block writes, the same number of
fully overwritten publications, 60,001,281 unnecessary high-lane snapshots and
50,028,481 unused logical-address snapshots. These overlapping counts are
opportunities, not latency estimates.

Reuse a checked host pointer only from a preceding containing write in the same
basic block. Both addresses have the same proven low-64-bit identity plus a
constant offset; the prior write validates bounds and write protection for the
whole new range. Stable backing cannot change in an admitted Call. Preserve
checks for every other write, including failures after an earlier effect.

Omit a publication only when a later same-block write completely contains it.
Successful execution reaches that overwrite; all private values and intervening
reads remain in original effect order. Intervening unknown aliases preserve
their bytes outside the final overwrite. Failure still replays the ordinary
Call before any private effect is published. Capture logical addresses only
when a later unknown-identity read can inspect them; capture/load the high value
lane only for accesses requiring it. Keep fixed private slots and all existing
admission, work, code, stack and instruction-budget limits.

Freeze 381 expected bytecode tests/profile (17 ignored), adding full-memory
alias and guard-reuse/fault controls in both persistent-register modes and every
instruction budget. Then build and qualify a new immutable candidate: full
workspace/Python controls, strict checking, exact original profiles, and the
predeclared 40-command changed-source token gate. Reconstruct the new emission
rather than requiring it to match the deliberately parked store bodies. Main
retains df4006e0; do not repeat the old candidate or start larger histories
unless the new primary passes.

Use the global lock, two Cargo workers/test threads, the protected ROOT target,
max(14 GiB, 8 GiB + twice allocated target) initial build reservation, and 8 GiB
child floor. Preserve every failure and bind sources, binaries and raw evidence.
