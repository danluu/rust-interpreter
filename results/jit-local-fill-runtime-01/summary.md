# Direct native local fills: same-artifact runtime comparison

The candidate wins all 18 JIT pairs on leaf-inlined bytecode. Three default-bytecode controls generate exactly the same native code size and execute the same number of native operations and entries. Interpreter controls show no consistent regression. These timings exclude frontend and export work; production-edit command comparisons are the next decision gate.

| Engine / artifact | Baseline median (s) | Candidate median (s) | Median paired change (ms) | Wins |
|---|---:|---:|---:|---:|
| jit:word64-default | 1.729818 | 1.723025 | -9.150 | 4/6 |
| jit:word64-inline8 | 1.096295 | 1.094806 | -2.951 | 5/6 |
| jit:sha1-inline8 | 0.461862 | 0.460566 | -1.296 | 4/6 |
| jit:word64-default-leaf-inline | 1.622955 | 1.468707 | -147.265 | 6/6 |
| jit:word64-inline8-leaf-inline | 1.024920 | 0.948760 | -75.996 | 6/6 |
| jit:sha1-inline8-leaf-inline | 0.438251 | 0.404915 | -33.226 | 6/6 |
| interpreter:word64-default | 14.616499 | 14.483165 | -96.075 | 5/6 |
| interpreter:sha1-inline8 | 4.757880 | 4.741949 | -1.346 | 3/6 |

Each artifact is run in a fresh process, with six alternating baseline/candidate pairs and a fixed 10-billion-instruction limit. All 96 commands return the expected unit result. Instruction counts and peak guest memory agree between builds. JIT counters are stable within each build. Every sample is retained; shared-host timing variability is visible in the raw pairs.

| Inlined artifact | Baseline native entries | Candidate native entries | Entries removed | Native bytes before / after |
|---|---:|---:|---:|---:|
| jit:word64-default-leaf-inline | 63,852,179 | 48,516,339 | 15,335,840 | 1,091,472 / 1,070,860 |
| jit:word64-inline8-leaf-inline | 32,187,064 | 24,113,034 | 8,074,030 | 1,120,644 / 1,103,940 |
| jit:sha1-inline8-leaf-inline | 9,749,212 | 5,291,417 | 4,457,795 | 372,060 / 364,556 |

The emitter recognizes only an exact, uninterrupted Local-address/literal-byte/literal-length sequence with distinct helper registers and a fill of at most 512 bytes entirely inside the active frame. Branches entering the sequence bypass the optimization. Native region and instruction-budget boundaries preserve ordinary VM semantics. Unrolled stores use the custom AArch64 emitter; there is no guest LLVM or host memory-fill fallback.

Qualification before this screen passed 88 bytecode tests, 24 option/cache/source-edit checks, 71 SIMD checks, 79 audit checks, 99 launcher checks, and 23,502 native differential/rejection commands each with leaf inlining disabled and enabled. Eleven instruction encodings independently matched the platform assembler. This is bounded operation support, not whole-program or whole-suite support.

[Validation](../jit-local-fill-validation-01.json). Raw measurements: `.work/jit-local-fill-runtime-01/`.
