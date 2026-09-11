# Native population count: identical-artifact runtime screen

The custom AArch64 JIT emits population count through 64 bits. The 128-bit operation retains the custom interpreter path. The exporter is byte-for-byte identical to the guarded baseline. All 104 bytecode tests pass, including masked inputs, destination aliases, neighboring 128-byte vector copies, live registers, exact loop budgets and assertion fault ordering.

The candidate improves **19/24 execution-only pairs** on four retained real test artifacts. Complete production-edit commands remain a separate gate. All timings, including the folded-trie regression, are retained. Profiled runs are separate from the six timed pairs per workflow.

| Workflow | Prior VM median (s) | New VM median (s) | Paired change (ms) | Wins | Counts moved to native |
|---|---:|---:|---:|---:|---:|
| fre-folded-literal-trie | 2.660 | 2.676 | +27.488 | 2/6 | 78,642 |
| fre-word64 | 1.422 | 1.416 | -9.941 | 5/6 | 324,264 |
| fre-word64-inline8 | 0.897 | 0.893 | -3.587 | 6/6 | 324,264 |
| pgrust-sha1-inline8 | 0.408 | 0.387 | -20.824 | 6/6 | 2,033,159 |

All input bytecode hashes match between modes. Total guest instruction counts and peak memory are unchanged. Profile totals agree across modes, with zero interpreted population counts in these four traces; the same number of host-to-generated-code entries is eliminated as counts moved to native. This demonstrates less dispatch, not a guaranteed command speedup. No A/A median is subtracted.

The emitter uses caller-saved v0 for per-byte counts and sums the eight byte lanes. Exact instruction words were checked using the local assembler and disassembler, outside guest compilation. The reduction follows the [Arm ADDV instruction definition](https://developer.arm.com/documentation/ddi0602/2023-09/SIMD-FP-Instructions/ADDV--Add-across-Vector-). The generated guest code remains entirely the custom emitter.

[Machine-readable evidence](summary.json).
