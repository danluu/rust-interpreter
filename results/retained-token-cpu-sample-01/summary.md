# Retained token-phrase CPU sample

The retained88c01c VM completed the original exhaustive token-phrase test while a separate diagnostic captured2,554 stacks at a requested1ms interval over3seconds. Only the newly spawned VM was targeted; PID, parent, command and cwd were checked. Instrumented wall time is excluded from benchmark evidence.

| Disjoint stack category | Samples | Share |
|---|---:|---:|
| Generated AArch64 code | 1259 | 49.3% |
| Dispatcher self, operation unresolved | 550 | 21.5% |
| Frame reservation, including clearing | 231 | 9.0% |
| Proven local argument copies | 175 | 6.9% |
| General argument copies | 61 | 2.4% |
| Return result copies | 135 | 5.3% |
| Other or unattributed memory copies | 54 | 2.1% |
| Guest heap management | 84 | 3.3% |
| JIT compilation | 4 | 0.2% |
| Switch lookup | 1 | 0.0% |

All generated program counters fall within the executable mapping captured from this same process. The exact retained binary disassembly identifies the frame-reservation, argument-copy and return-copy call sites. Frame reservation includes119 clearing samples; this subset must not be added again. The dispatcher’s550 self samples combine several PCs and remain unattributed to particular bytecode operations.

Call frame setup, argument copying and return copying together account for602 samples (23.6%). This supports a targeted investigation of call-boundary work. It does not predict an equivalent speedup. First quantify result sizes, caller-local return destinations and argument extents from the exact bytecode and existing execution profile. A zero-byte result copy is a possible simple target; a caller-local return proof is a separate alternative. Preserve argument ordering, zero initialization, nested calls, TLS callbacks, errors and exact budgets.

[Parked memory-instruction experiment](../native-memory-parts-01/summary.md). Its instruction-count reduction yielded little edited-command benefit, which prompted this CPU check.
