# Combined aggregate graph agrees with independent projections

All nine controls pass in debug/release, plus the 13 legacy memory-proof and five
scalar-IR controls in release. Every aggregate fixture now compares one combined
graph with the separate projection oracle and ordinary interpreter, including
full bytes, original PC counts, padding, branches and fault/budget exits.

The ninth control verifies identical small-result native words in profiled and
unprofiled modes and requires both legacy native entry points to reject larger
returns. No aggregate plan can write through the existing 16-byte result ABI.
Return-lane uses participate in register liveness. No aggregate native code is
published or executed, and no original-project benchmark runs.

Proceed to the actual combined-plan census before native ABI work. The four
commands and all source/log bindings are closed. [Summary](summary.json),
[closure](closure.json), [combined-model contract](../../benchmarks/experiments/scalar-aggregate-model/COMBINED.md).
