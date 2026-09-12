# Next: measure scalar values forced through memory at call boundaries

Whole-call expansion is parked. Token improves complete-command wall time by
5.23%, beyond its 3.83% A/A envelope but below the fixed 10% target. Folded's
0.56% difference is inside A/A variation. Keep the candidate and every pair;
do not tune its thresholds or integrate it. Root remains `5b2330c` / `9637b0ac`.

The completed token histories show a paired execution reduction of 291.9 ms
and 62.7 ms more Cargo time. Folded saves 26.2 ms execution and adds 12.9 ms
Cargo. These stage medians are observations and do not sum exactly to the
command median. Fewer native Calls alone did not yield the required benefit.

Native resumable Calls already push/pop guest frames without returning to the
Rust VM. A proposal to add native branches would repeat existing machinery.
The current scalar promoter, however, explicitly excludes arguments and the
result, and excludes primitive locals passed to calls or aggregate operands.
This forces values through frame storage at precisely the remaining boundary.

First build a diagnostic observer from the integrated source. Keep its guest
artifact bytes identical to the qualified original artifacts. Record typed MIR
eligibility for argument/result scalar promotion, separately from ordinary
local promotion and from a broader scalar-layout classification. Apply the
existing address-exposure/operand restrictions; never infer Rust privacy merely
from bytecode slot size. Bind records to function IDs and exact lowered bodies,
not pretty names, which can collide. Reconcile with the two original profiles.

Bound the observer and report exhausted analyses explicitly. Rank dynamic
argument/result loads, stores, copies and native boundary bytes separately.
Report rejected/escaping/address-taken slots and coverage; counts are not a
latency forecast. Preserve the original randomness and no new timing claims.

Use that census to choose between (a) loading private scalar parameters into
virtual registers once and storing a scalar result at Return, retaining the
existing memory ABI; and (b) a new scalar value-passing ABI if repeated boundary
copies dominate. The former still pays initial/final copies and may be too small.
The latter requires explicit bytecode versioning/validation, interpreter and
native support, indirect calls, entry/return initialization and partial-fault
semantics. Neither should weaken alias, budget, profile or strict Rust checks.

Before any implementation timing, freeze a new concrete plan and qualifications.
Use real edited commands, fresh A/A controls, a fixed meaningful improvement
target, and separate held-out guards. Do not reinterpret the parked experiment's
gate. Keep full libtest, unwinding, threads, broad OS/FFI and fastest-native
qualification as open work; no external guest interpreter or LLVM backend.
