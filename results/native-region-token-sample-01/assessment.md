# Native region runtime samples

Three fresh original token executions of `26833c3` / `2f31c6a0` passed.
The captured windows contain 7,679 thread samples. All observed
generated self PCs resolve inside the same process’s recorded live JIT arena.
These perturbed windows are diagnostics, not end-to-end timings.

| Disjoint category | Captured share |
| --- | ---: |
| generated code | 61.7% |
| native boundary self | 11.2% |
| dispatcher self | 10.4% |
| heap inclusive | 5.3% |
| memory copy inclusive | 4.5% |
| frame reservation inclusive | 3.8% |
| other host self | 2.9% |
| jit preparation inclusive | 0.3% |

Self counts subtract immediate child counts; selected helper categories include
their descendants. The categories differ from the older host-call-site report,
so percentage subtraction against that report is not a before/after estimate.
Grouped host PCs remain unresolved. Generated counts do not identify opcodes.

Folded still spends substantial captured time in VM frame reservation/zeroing;
token spends most captured time in generated code. Next capture emitted bytes
and entry ranges from the sampled process to separate native setup/copy loops
from ordinary generated arithmetic/memory code before selecting the next change.

[Verified sample records](summary.json) · [E2E gates](../native-region-e2e-01/assessment.md)
