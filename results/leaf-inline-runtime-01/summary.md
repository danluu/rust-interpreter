# First leaf-inlining prototype: runtime screen

The transform runs outside the engine/exporter and rewrites copies of previously retained bytecode. Both versions execute with the same qualified VM. It resets a disjoint inline frame on every invocation, copies arguments in order, clones scalar leaf control flow, and copies the result back.

| Engine / workload | Original (s) | Inlined (s) | Median paired change (ms) | Inlined wins |
|---|---:|---:|---:|---:|
| jit:word64-default | 1.729663 | 1.944336 | 220.307 | 0/6 |
| jit:word64-inline8 | 1.101757 | 1.313557 | 216.960 | 0/6 |
| jit:sha1-inline8 | 0.460676 | 0.475232 | 17.588 | 0/6 |
| interpreter:word64-default | 14.521392 | 15.314741 | 762.988 | 0/6 |
| interpreter:sha1-inline8 | 4.688787 | 4.712981 | -10.843 | 4/6 |

All 60 commands return the expected value; statistics are repeatable for each artifact. Instruction counts and frame/register requirements change under the transform and are reported separately. Fourteen prototype/proof tests cover aliases, loops, initialization, diagnostics, budget tails and exclusions.

| Workload | Native entries before / after | Native code bytes before / after | Instructions before / after |
|---|---:|---:|---:|
| word64-default | 72,828,899 / 64,338,611 | 894,776 / 1,112,112 | 3,336,017,284 / 3,470,008,718 |
| word64-inline8 | 35,640,770 / 32,673,460 | 942,108 / 1,137,908 | 2,892,954,629 / 2,974,031,005 |
| sha1-inline8 | 14,128,429 / 9,749,920 | 276,820 / 377,232 | 1,378,275,772 / 1,422,930,915 |

The prototype loses every JIT pair and is rejected as-is. It has not been integrated into the exporter or tested in complete production-edit commands. The next diagnostic checks whether lost Local-address facts add guards and force unnecessary caller register initialization. That is a hypothesis, not measured CPU attribution.

These are six alternating runtime pairs on a shared host, including bytecode loading and JIT construction but excluding transformation and Cargo/frontend work. All samples and load readings remain in the raw records.

[Transformation provenance](../../.work/leaf-inline-prototype-artifacts-01/summary.json), [structural screen](../leaf-inline-analysis-01/summary.md), [raw summary](summary.json).
