# Original-test profiles match

Three new candidate profiles match the three retained adopted-runtime controls:
original assertions, every logical PC count, peak guest memory, entropy calls and
bytes, and complete emitted-code mapping. The closure verifies 65 frozen inputs
and 24 artifacts. The controls were reused through exact binary and evidence
hashes, not executed again.

Scalar Calls remain 11,227,102 / 16,298,574 / 1,585,153 for token block, token
exhaustive and folded prefilter. Ordinary native code shrinks by 22,724 / 29,268 /
1,188 bytes. Single profiled JIT preparation counters increase by 30.64 / 35.68 /
6.10 ms relative to retained controls. These noncontemporaneous, instrumented
observations are diagnostic and do not establish a performance effect.

Proceed to the fixed changed-source primary, which includes preparation and
execution in full command wall and child CPU time. See [summary.json](summary.json)
and [closure.json](closure.json).
