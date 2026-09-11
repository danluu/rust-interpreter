# JIT assertions: runtime comparison

The custom AArch64 emitter now handles assertion conditions within generated regions, retaining full 128-bit truth, original messages, and failure/budget order. All 58 bytecode tests, 23,277 native differential/rejection commands, and 93 launcher checks pass. One new test initially assumed a two-operation tail would be compiled; its coverage expectation was corrected without changing the engine.

| Identical bytecode | Before | After | Candidate pair wins |
|---|---:|---:|---:|
| word64-default | 2.290 s | 2.286 s | 3/5 |
| word64-inline8 | 1.574 s | 1.526 s | 5/5 |
| sha1-inline8 | 0.696 s | 0.656 s | 5/5 |

Default-threshold word64 is essentially flat. The eightfold word64 configuration improves about 3%, and SHA-1 about 6%; both win all five pairs. Each pair uses identical production-workflow bytecode, with unchanged total instruction count and peak guest memory. Generated code grows by about 1.1–1.3 KB.

Separate operation profiles record zero interpreted assertions in both eightfold workloads, down from 6.26 million for word64 and 17.96 million for SHA-1. JIT entries fall from 109.52 to 106.79 million and 75.47 to 67.09 million, respectively. Calls, returns, copying, and short control-flow regions remain substantial. Operation counts are not CPU-time measurements.

These modest runtime gains do not establish an end-to-end win. All nine production edit/test workflows pass, but an observed interpretation slowdown still requires a controlled comparison. [Complete command results](../e2e-jit-assertions-corpus-01/summary.md). Original test inputs and frontend checks remain enabled.

[Detailed validation and raw records](../jit-assertions-validation-01.json).

Three alternating interpreter pairs confirm a regression on identical bytecode: word64 measured 15.803 → 17.056 s, and SHA-1 5.326 → 5.562 s. The candidate lost all three pairs in both workloads, with identical instruction counts and guest memory. This version is not retained as-is. The next experiment moves error formatting out of the inlined JIT transition; an engine-specific loop specialization is a separate alternative.
