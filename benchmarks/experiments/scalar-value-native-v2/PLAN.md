Implement the scalar ABI in the custom AArch64 emitter using the qualified
serialized CLI source. This is an isolated correctness milestone. Caller
operands still provide addresses; caller value operands and compiler promotion
remain mandatory before a real-workflow performance decision.

Return implicitly reads the ABI result in both ordinary register forwarding and
bounded CFG liveness. Resumable calls initialize the result before ordered scalar
inputs (including aliases), use the input-aware zeroing proof, and retain the
existing explicit guest frame stack and decline-before-progress guards. Scalar
returns publish their value through the original checked destination. Root and
TLS returns use the shared VM. Indirect calls keep the existing VM path.

Support ordinary and resumable JIT modes, with and without persistent registers.
Reject the historical native tree/stub modes explicitly. Preserve version-5
behavior and its complete test suite. Qualify 310 debug/release tests (one ignored):
existing scalar reference fixtures compare every instruction budget and per-PC
profiles across all four native modes; five additional tests require actual hot
native transitions, cover all scalar widths, implicit result liveness, ordered
faults, code/memory/depth limits and indirect signatures. Include original legacy
artifact roundtrips. This is not a performance measurement or a runtime release.

Freeze the recipe and copied source, record owned processes, use the nonblocking
benchmark lock, require 12 GiB initially and preserve the 8 GiB floor. Record any
failure before changing the recipe and use a fresh run ID for each revision.

Revision 2 corrects only the test harness: Limits deliberately has no Clone
implementation. Copy every option explicitly in the test helper. The failed
first build is retained with its unchanged recipe and terminal receipt.
