# Register initialization: six production workflows, five projects

Every workflow passed its existing tests after five cumulative production edits.
Test source stayed unchanged; every engine rejected the wrong production edit.
All commands used one immutable build. Source snapshots were verified restored.

| Workflow | Native seconds | Interpreter seconds | JIT seconds |
|---|---:|---:|---:|
| [fre-word64](../e2e-workflow-fre-word64-register-init-01/summary.md) | 1.674 | 17.369 | 3.908 |
| [pgrust](../e2e-workflow-pgrust-register-init-01/summary.md) | 0.639 | 0.829 | 0.564 |
| [fre-class-sequence](../e2e-workflow-fre-class-sequence-register-init-01/summary.md) | 1.321 | 0.742 | 0.744 |
| [nushell](../e2e-workflow-nushell-register-init-01/summary.md) | 0.624 | 0.428 | 0.430 |
| [ruff](../e2e-workflow-ruff-register-init-01/summary.md) | 5.805 | 3.149 | 2.969 |
| [rg-aot](../e2e-workflow-rg-aot-register-init-01/summary.md) | 0.554 | 0.191 | 0.193 |

Medians cover complete edited commands: Cargo, checking/lowering, launcher, and
execution. Each mode has independent caches. Word64 uses explicit MIR level 3
with normal frontend and overflow checking, retaining all exhaustive tests. It
now uses the installed sysroot. Nushell keywords and Ruff use the separately
installed standard-library MIR metadata (10.997 s setup excluded here).

The register-initialization change reduced word64 JIT execution on the same
artifact from 3.734 to 3.147 s in three interleaved pairs. Its full edit median
changed from 4.538 to 3.908 s; native in this run was 1.674 s. The guest still
loses the longer compute workflow. Shorter workflow differences from the previous
build include shared-host compilation variation; this run does not establish
a statistically significant change in those cases. Ruff native and custom
commands were both slower than the preceding common-build run.

This qualifies selected workflows, not whole applications or suites. Five
samples per mode on a shared host are not confidence intervals. Private rg-aot
source, selected names, and detailed records remain under `.work`.

[Register initialization checks](../register-init-validation-01.json).
