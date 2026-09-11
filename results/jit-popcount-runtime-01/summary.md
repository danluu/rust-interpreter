# Population count: controlled runtime comparison

This candidate is not retained. SHA-1 improves, but both paired word64 build/test workflows regress. The qualified call-copy build remains selected. The full nine-workflow corpus was not run for this rejected candidate.

Six alternating immutable-VM pairs per workload and engine, using the same saved production bytecode. All 60 commands pass and agree on values, total virtual instructions, and guest-memory peaks. JIT operation coverage changes as expected. This measures runtime, not compilation.

| Engine / workload | Before (s) | After (s) | Median paired change (ms) | Candidate wins |
|---|---:|---:|---:|---:|
| jit:word64-default | 2.204356 | 2.191984 | -14.075 | 4/6 |
| jit:word64-inline8 | 1.478734 | 1.471108 | -5.586 | 3/6 |
| jit:sha1-inline8 | 0.634458 | 0.620001 | -16.821 | 6/6 |
| interpreter:word64-default | 14.522421 | 14.577338 | -27.481 | 3/6 |
| interpreter:sha1-inline8 | 4.759512 | 4.781298 | 70.088 | 2/6 |

SHA-1 JIT improves in every pair; word64 and interpretation are mixed and close to the baseline. Keep all samples and host-load readings. These small samples on a shared host are not confidence intervals. Median paired differences need not equal differences between medians.

The VM file size remains 764,944 bytes. Emitted guest code grows by 160 bytes for default word64, 320 bytes for inlined word64, and 96 bytes for SHA-1. The exporter binary is byte-for-byte unchanged.

[Native and launcher validation](../jit-popcount-validation-01.json). [Paired build/test commands](../paired-popcount-e2e-01/summary.md).
