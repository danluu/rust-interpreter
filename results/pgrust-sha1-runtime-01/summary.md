# Pgrust SHA-1: an independent runtime workload

Both original SHA-1 tests pass after five production refactors, with unchanged
reference vectors including the million-byte input and seven-byte incremental
chunks. Perturbing a round constant fails the original reference test in every
engine. Complete edited-command medians are **0.781 s native, 1.255 s JIT, and
5.726 s interpreted**. The custom commands explicitly use eightfold MIR inlining
thresholds and the reusable metadata sysroot; ordinary checking stays enabled.
[Production workflow and cold/setup costs](../e2e-workflow-pgrust-sha1-inline8-01/summary.md).

Five alternating identical-bytecode pairs compare the preceding VM with the
forced-wrapper-inline VM: **0.812 versus 0.694 s**, winning all five pairs.
Both execute 1,378,275,772 virtual instructions, peak at 1,019,120 guest bytes,
and generate 231,000 bytes of code. This extends the wrapper's runtime evidence
to a second project's original workload. Native remains faster end to end.

A separate instrumented run records 17,964,866 interpreted assertions,
5,539,697 calls, 2,033,201 unary operations (population counts), and 1,016,399
dynamic copies. Assertions and population count are not yet emitted by the JIT;
their boundaries can also leave short neighboring regions interpreted. These
counts suggest direct JIT assertion handling as a candidate shared with word64,
which retains 6.26 million interpreted assertions after stronger MIR inlining.
They are operation counts, not CPU-time attribution or a promised speedup.

Raw pairs, hashes, command records, and the separate profile are retained in the
JSON. The benchmark adds no invented repetitions or shortened inputs.
