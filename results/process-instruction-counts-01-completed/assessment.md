# Whole-process retired instructions: exhaustive token test

All three original native/JIT assertion pairs pass. The median paired custom/native instruction ratio is7.1317; the cycle ratio is4.3984. The raw per-pair ratios are preserved in [the summary](summary.json).

| Process | Median retired instructions | Median cycles | Median cycles/instruction |
| --- | ---: | ---: | ---: |
| native | 11,121,273,116 | 2,509,966,850 | 0.22570 |
| jit | 79,319,446,861 | 11,081,979,517 | 0.13971 |

The custom process executes far more machine instructions while spending fewer cycles per instruction. This supports reducing emitted instruction volume before redesigning the memory model to address presumed stalls. It does not attribute all extra instructions to one mechanism. The next candidate uses a proven capacity allowance to remove repeated call-limit bookkeeping, preserving independent frame limits and exact logical budgets.

Scope is the entire target process, including native loader/libtest setup and custom decode, analysis, code generation and guest execution. Parent-launcher work is excluded. Ordinary OS entropy is used; these are not exact-entropy differential runs or pure guest-only counts. No Cargo checking, export, editing or build latency is measured here. Adoption still needs complete edited-command comparisons.

The installed SDK's per-process API returned stable final instruction/cycle counts from each naturally exited, unreaped child. Each PID matched its launcher, waitid result and eventual waitpid result. Positive timestamps/counters, two bounded spin checks and an intentional exit-seven child qualified the accounting. No process was attached, signaled, paused or injected. Apple's [Recount documentation](https://github.com/apple-oss-distributions/xnu/blob/main/doc/observability/recount.md) describes the instruction accounting; its [resource implementation](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/kern_resource.c) describes cached exit statistics.

The initial controller stopped after the first complete pair because its parser required optional logical VM statistics, which were disabled. Both original assertions and hardware reads had already succeeded. The corrected parser validated their preserved outputs, then an explicit continuation executed only the four outstanding commands in their original order. No completed command was repeated or replaced; all nine target commands and both controller histories remain recorded. The old failure has [its own receipt](../process-instruction-counts-01/summary.json).
