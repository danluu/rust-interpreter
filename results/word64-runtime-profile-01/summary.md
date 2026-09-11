# Why the full fre word64 workflow is slow

The twelve unchanged existing tests execute billions of bytecode operations.
The completed production-edit benchmark measured 13.164 s JIT, 27.465 s
interpreted, and 1.707 s native; native test execution was about 0.21 s.
[End-to-end baseline](../e2e-workflow-fre-word64-01/summary.md).

Optional instrumented execution counted the following work. These are exact
operation counts for the recorded artifacts, not estimates of time spent in
each operation. Profile overhead is excluded from performance claims.

| Artifact | Bytecode instructions | Guest calls including entry | Local-address operations | Interpreted operations | Initialized frame/register bytes over run |
|---|---:|---:|---:|---:|---:|
| Default MIR, final production edit | 5,182,568,923 | 126,591,560 | 1,915,253,448 | 757,297,941 | 99,960,460,902 |
| MIR level 3, original source | 3,481,662,564 | 38,981,948 | 1,299,471,598 | 298,369,439 | 79,327,625,985 |

The initialization totals multiply actual entry counts by each function's
register payload and frame size. They exclude padding and allocator overhead;
they are cumulative bytes, not peak memory. The two artifacts represent
different source states, so the table is diagnostic rather than a paired
production-edit comparison. Both preserve the original test inputs.

An uninstrumented initial probe found MIR level 2 removed only about 3% of
operations and still took about 12 s to execute. Level 3 enabled MIR inlining
and reduced guest execution to about 6 s. The probe used the same debug profile
and overflow checks, with no LLVM guest code generation. Its reused-artifact
second commands are not edit-to-test benchmarks. The explicit setting remains
optional pending full production-edit comparison.

The VM currently allocates and frees a register vector at every guest call.
A reusable register stack is the next bounded change to test. Zero initialization,
caller isolation, instruction accounting, and live-memory limits must remain
unchanged. Constant/local-address elimination and fewer JIT/interpreter
transitions are subsequent possibilities if execution measurements justify them.
