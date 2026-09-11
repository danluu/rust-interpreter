The fresh original workload passes with immutable tool `78e60cdd`, matching the sampled artifact and runtime options. Its instrumented profile reconciles 13,347,154,631 native and 22,417,721 interpreted instructions exactly with VM statistics.

Copy and CopyDynamic account for 19,769,609 interpreted instructions (88.19%). Variant labels group recorded operations only; operand and memory-safety analysis requires typed bytecode. No timings or speedup estimates follow.

| Interpreted variant | Executions |
| --- | ---: |
| CopyDynamic | 12,054,220 |
| Copy | 7,715,389 |
| CallIndirect | 875,485 |
| Allocate | 563,344 |
| Deallocate | 563,344 |
| Reallocate | 473,389 |
| Binary | 170,143 |
| Call | 1,645 |
| FillBytes | 398 |
| Switch | 272 |
| CpuFeatureQuery | 84 |
| RandomBytes | 3 |
| ResetThreadLocals | 3 |
| Unary | 1 |
| Return | 1 |

[Counts, exact commands and evidence](summary.json) · [Selected experiment](../../benchmarks/experiments/resumable-native-calls/COPY-TRANSITIONS-NEXT.md)
