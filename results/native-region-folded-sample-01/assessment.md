# Native region runtime samples

Three fresh original folded executions of `26833c3` / `2f31c6a0` passed.
The captured windows contain 2,565 thread samples. All observed
generated self PCs resolve inside the same process’s recorded live JIT arena.
These perturbed windows are diagnostics, not end-to-end timings.

| Disjoint category | Captured share |
| --- | ---: |
| generated code | 48.1% |
| frame reservation inclusive | 21.9% |
| native boundary self | 12.0% |
| dispatcher self | 9.3% |
| other host self | 4.8% |
| memory copy inclusive | 3.7% |
| heap inclusive | 0.1% |

Self counts subtract immediate child counts; selected helper categories include
their descendants. The categories differ from the older host-call-site report,
so percentage subtraction against that report is not a before/after estimate.
Grouped host PCs remain unresolved. Generated counts do not identify opcodes.

Folded still spends substantial captured time in VM frame reservation/zeroing;
token spends most captured time in generated code. Next capture emitted bytes
and entry ranges from the sampled process to separate native setup/copy loops
from ordinary generated arithmetic/memory code before selecting the next change.

[Verified sample records](summary.json) · [E2E gates](../native-region-e2e-01/assessment.md)
