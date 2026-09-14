# Qualify the private aggregate native ABI before widening Call selection

The combined model and exact candidate census are closed. Implement a contiguous
64-byte private payload followed by steps/profile bits. Derive every shared offset
from the Rust layout, including Call inputs, stack bounds and the legacy bridge.
Keep wide emission behind an explicit test-only entry in this qualification.
Production scalar eligibility remains unchanged. The existing small calls use
the new shared layout; neither ABI nor timing equivalence is assumed.

Emit each original body once, with ordered <=16-byte result lanes. Preserve all
fault roots and original PC counts. Reject oversized or inconsistent result
shapes before publication. Native controls compare full result bytes, private
payload sentinels on failure, complete output on short admission, surrounding
canaries, preserved registers and SP. Both the standalone and adapted private
Call conventions run with profiles enabled and disabled. Include all widths
0..64, 468 independently computed overlapping copies, branch joins, unequal and
nonmonotonic return paths, all short budgets, eight profile words, dead division,
late assertions, Trap, 64 arguments, 1 KiB frames and logical address bits.

Run six focused controls in debug/release, then the complete bytecode library
suite in debug/release. Require every nonignored test to pass, at least the
adopted 345 tests plus these six and the nine aggregate model controls; record
the exact test and ignored counts. Existing ignored diagnostics stay ignored.
No original-project guest command or performance measurement occurs here.

Use the global lock, two Cargo workers, no entropy injection, immutable source
hashes and only the shared owned target. Require max(14 GiB, 8 GiB + twice its
allocated size) before each build and an 8 GiB child floor. Close pass or failure
before editing or proceeding. Wide Call selection and its full memory/fault
qualification are the next step, followed by the prior strict/profile and
prospective changed-source exhaustive primary plan.
