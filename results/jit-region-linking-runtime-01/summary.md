# Linked native blocks: controlled runtime comparison

Compiled successors in the same guest function now branch directly to one another. Every block checks and consumes its virtual-instruction budget. Short or unsupported successors, calls, returns, and allocations still use the VM. Budget tails fall back instruction by instruction. The guest storage stays fixed throughout each native chain.

| Engine / workload | Before (s) | After (s) | Median paired change (ms) | Candidate wins |
|---|---:|---:|---:|---:|
| jit:word64-default | 2.195045 | 1.724923 | -470.828 | 6/6 |
| jit:word64-inline8 | 1.471693 | 1.092914 | -369.394 | 6/6 |
| jit:sha1-inline8 | 0.645667 | 0.460032 | -185.775 | 6/6 |
| interpreter:word64-default | 14.541950 | 14.492527 | -111.597 | 4/6 |
| interpreter:sha1-inline8 | 4.726133 | 4.728770 | 26.615 | 2/6 |

Six alternating pairs per workload/engine; all 60 commands pass. Every pair uses identical bytecode and agrees on value, virtual instructions, compiled virtual instructions, compiled operation coverage, and peak guest memory. All samples and host-load readings are retained. These are runtime measurements, not complete build/test times, and six samples on a shared host are not confidence intervals.

| Workload | Baseline native entries from saved trace | Candidate native entries |
|---|---:|---:|
| word64-inline8 | 106,794,089 | 35,640,770 |
| sha1-inline8 | 67,092,799 | 14,128,429 |

Baseline entry counts come from the retained, bytecode-verified trace before call-copy optimization; that change preserved instruction flow and compiled coverage. Candidate counts are measured directly by the new `jit_entries` statistic. Profiling now increments every linked block inside generated code, and the tests verify its instruction totals against ordinary execution.

| Workload | Before JIT construction (ms) | After (ms) |
|---|---:|---:|
| word64-default | 3.079 | 3.172 |
| word64-inline8 | 3.289 | 3.483 |
| sha1-inline8 | 1.118 | 1.158 |

The release VM is 764,480 bytes, 464 bytes smaller than the qualified baseline. Emitted guest code grows by about 142 KB for word64 and 45 KB for SHA-1. The 16 MiB code limit remains. The candidate passes 73 bytecode tests, 23,502 native differential/rejection commands, and 99 launcher checks, including an assembly wrapper that checks the generated code preserves x19 and SP on normal, budget, memory, division, and assertion exits. The assembler is only a test oracle; guest code uses the hand-written emitter.

[Validation](../jit-region-linking-validation-01.json).
