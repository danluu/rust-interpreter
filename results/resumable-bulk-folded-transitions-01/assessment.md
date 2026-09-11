The fresh original workload passes with immutable tool `78e60cdd`, matching the sampled artifact and runtime options. Its instrumented profile reconciles 4,138,317,516 native and 85,769 interpreted instructions exactly with VM statistics.

Copy and CopyDynamic account for 4,772 interpreted instructions (5.56%). Variant labels group recorded operations only; operand and memory-safety analysis requires typed bytecode. No timings or speedup estimates follow.

| Interpreted variant | Executions |
| --- | ---: |
| Allocate | 38,735 |
| Deallocate | 38,735 |
| Copy | 4,726 |
| CallIndirect | 2,513 |
| Call | 444 |
| Reallocate | 263 |
| Binary | 171 |
| CpuFeatureQuery | 84 |
| CopyDynamic | 46 |
| FillBytes | 32 |
| ResetThreadLocals | 18 |
| Unary | 1 |
| Return | 1 |

[Counts, exact commands and evidence](summary.json) · [Selected experiment](../../benchmarks/experiments/resumable-native-calls/COPY-TRANSITIONS-NEXT.md)
