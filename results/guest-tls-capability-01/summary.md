# Guest TLS capability and real production edits

Guest C/System allocation, errno, and TLS callbacks now execute Rust's destructor
list and thread cleanup. All 17 formerly runtime-blocked fre tests pass against
fresh native controls. The complete survey has **320 passed, 62 lowering blocked,
7 ignored**; no prior passing test regressed. Original tests and tracing remain
unchanged. [Coverage](../audit-execution-fre-guest-tls-01/summary.md).

The separate `--run-try-callbacks` option requires `--trap-unsupported-calls`.
Type/borrow checking remains strict. Only normal callback return produces false;
actual panic, unwinding and VM faults fail the command. Guest callbacks never enter
the host TLS ABI. Queue, frame and instruction limits apply during cleanup.
119 bytecode tests, 489 allocator differential commands, 233 raw TLS checks and
245 standard TLS/try checks passed in the staged builds recorded in JSON. Both 23,502-command native suites and the other broad checks passed on the
combined build. Fifteen launcher checks also verify option on/off/reverts, ambient
flag isolation, actual-panic failure and rejection of an uncalled borrow error.
[Broad validation](../guest-tls-default-validation-01.json).

Five real production edits use all 17 newly enabled original tests, alongside an
incorrect-edit control. Every custom engine rejects the incorrect edit and uses
identical bytecode for matching edits. Source is restored afterward.

| Engine | Median edited command | Cold command sample |
|---|---:|---:|
| Native | 1.884 s | 7.046 s |
| Custom JIT | 2.422 s | 5.854 s |
| Custom interpreter | 10.625 s | 14.188 s |

The JIT loses four of five warm comparisons. Its median paired penalty is 483 ms;
the only win is 5.5 ms. JIT Cargo and execution medians are 1.025 s and 1.308 s.
The cold sample reuses prepared standard-library MIR. No broad speedup is claimed.
[Every edited-command sample](../e2e-workflow-fre-guest-tls-01/summary.md).

Profiles of the edited artifact count 3.072 billion guest operations, 120.55 million
interpreted operations and 40.54 million interpreted calls. Tiny iterator wrappers
account for many calls. Interpreter/JIT logical per-instruction profiles match for
root, batch and production controls. Thread cleanup executes exactly 1, 3 and 17
times respectively. These instrumented profiles are diagnostic, not timings.

Next evaluate structural forwarding-call elimination without frame/code growth,
then bounded inlining across call chains and MIR optimization on the same
production edits, while preserving frame/growth limits and the broader project
corpus. The capability gain is retained as experimental; warm performance needs
improvement. Machine-readable provenance is in summary.json.
