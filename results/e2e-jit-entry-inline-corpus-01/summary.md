# JIT transition helper: six workflows, five projects

Every workflow passed its unchanged existing tests after five cumulative
production edits. Every engine also rejected the wrong production edit. Tool
and benchmark sources were frozen throughout; all owned source pins were
verified restored afterward. Builds and commands ran serially.

| Workflow | Native seconds | Interpreter seconds | JIT seconds |
|---|---:|---:|---:|
| [fre-word64](../e2e-workflow-fre-word64-jit-entry-inline-01/summary.md) | 1.703 | 17.509 | 3.705 |
| [pgrust](../e2e-workflow-pgrust-jit-entry-inline-01/summary.md) | 0.662 | 0.814 | 0.546 |
| [fre-class-sequence](../e2e-workflow-fre-class-sequence-jit-entry-inline-01/summary.md) | 1.325 | 0.760 | 0.729 |
| [nushell](../e2e-workflow-nushell-jit-entry-inline-01/summary.md) | 0.645 | 0.429 | 0.419 |
| [ruff](../e2e-workflow-ruff-jit-entry-inline-01/summary.md) | 5.458 | 2.940 | 2.850 |
| [rg-aot](../e2e-workflow-rg-aot-jit-entry-inline-01/summary.md) | 0.534 | 0.197 | 0.197 |

These are complete edited-command medians, including Cargo, frontend checking,
lowering, launcher, and execution. Each engine has independent caches. Word64
retains all twelve exhaustive tests and uses explicit MIR level 3 with ordinary
frontend and overflow checking. It uses the installed sysroot. Nushell and Ruff
use the separate standard-library MIR metadata; its 10.997 s original setup is
excluded. Cold successful command times are recorded separately in each result.

The retained change allows the host compiler to inline the checked JIT entry/
return helper. Guest machine code and virtual instruction counts are unchanged.
Five interleaved runtime pairs on one artifact changed the median from 3.033 to
2.887 s; four of five favored the candidate, with a slower first candidate run.
The word64 complete-command median changed from 3.908 to 3.705 s. Its measured
JIT execution median is 2.891 s, and Cargo's median is 0.788 s. Native still wins
that workflow at 1.703 s. Smaller workflow differences include shared-host
compilation variation and do not establish separate runtime improvements.

Two copy optimizations were removed after they failed paired runtime comparisons.
Overlap, invalid-range, read-only-memory, and empty-copy tests remain. The retained
runtime passes all bytecode checks, 5,415 differential commands against native
Rust (including expected rejections), and all 93 launcher checks.

These are selected workflows within large workspaces, not complete application
or suite support. Five samples per mode on a shared host are not confidence
intervals. Private rg-aot source, selected names, and detailed logs stay in `.work`.

[Qualification](../jit-entry-inline-validation-01.json),
[phase timings](../jit-entry-inline-word64-stages-01.json),
[profile and rejected copy experiments](../word64-cpu-profile-02/summary.md).
