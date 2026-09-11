# Leaf inlining with Local rematerialization: runtime screen

The transform runs outside the engine/exporter and rewrites copies of previously retained bytecode. Both versions execute with the same qualified VM. It resets a disjoint inline frame on every invocation, copies arguments in order, clones scalar leaf control flow, and copies the result back.

| Engine / workload | Original (s) | Inlined (s) | Median paired change (ms) | Inlined wins |
|---|---:|---:|---:|---:|
| jit:word64-default | 1.733565 | 1.624339 | -110.069 | 6/6 |
| jit:word64-inline8 | 1.374173 | 1.298061 | -93.827 | 5/6 |
| jit:sha1-inline8 | 0.713276 | 0.533396 | -179.880 | 6/6 |
| interpreter:word64-default | 15.531923 | 15.824617 | 272.336 | 1/6 |
| interpreter:sha1-inline8 | 4.795676 | 4.900197 | 91.882 | 0/6 |

All 60 commands return the expected value; statistics are repeatable for each artifact. Instruction counts and frame/register requirements change under the transform and are reported separately. Fourteen prototype/proof tests cover aliases, loops, initialization, diagnostics, budget tails and exclusions.

| Workload | Native entries before / after | Native code bytes before / after | Instructions before / after |
|---|---:|---:|---:|
| word64-default | 72,828,899 / 63,852,179 | 894,776 / 1,091,472 | 3,336,017,284 / 3,519,861,795 |
| word64-inline8 | 35,640,770 / 32,187,064 | 942,108 / 1,120,644 | 2,892,954,629 / 3,004,804,012 |
| sha1-inline8 | 14,128,429 / 9,749,212 | 276,820 / 372,060 | 1,378,275,772 / 1,439,744,855 |

The revision wins 17/18 JIT pairs but slightly regresses interpretation. It repeats proven Local definitions before argument copies and at the result join, preserving register values and eliminating the added caller-register clearing in all three artifacts. It has not yet been integrated into the exporter or tested in complete production-edit commands. Inline8 and SHA-1 timing varied substantially on the shared host; those gains are less certain than default word64. The next experiment will expose an explicit export option for JIT use, keeping the default artifact unchanged.

These are six alternating runtime pairs on a shared host, including bytecode loading and JIT construction but excluding transformation and Cargo/frontend work. All samples and load readings remain in the raw records.

[Transformation provenance](../../.work/leaf-inline-prototype-artifacts-01/summary.json), [structural screen](../leaf-inline-analysis-01/summary.md), [raw summary](summary.json).
