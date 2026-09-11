# Word64 CPU profile after checked division

A one-second sample of the qualified VM executing the archived final production-edit artifact captured 769 samples. This is a diagnostic, not a benchmark result.

| Sample location | Approximate share |
|---|---:|
| Generated code | 31% |
| VM loop | 29% |
| Copies and memmove | 23% |
| JIT entry helper | 9% |
| Frame reservation and memset | 7% |

Unknown sampled addresses were verified against the VM's executable JIT mapping. The short profile supports investigating fewer guest calls and less control-flow overhead; it does not establish a speedup for a proposed change. The next experiment compares higher MIR inlining cost limits using complete production-edit commands, including compilation, execution, code size, and memory.

[Qualified division benchmarks](../e2e-jit-division-corpus-01/summary.md), [validation and paired runtime](../jit-division-validation-01.json).
