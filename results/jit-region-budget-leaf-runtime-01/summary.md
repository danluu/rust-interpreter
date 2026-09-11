# Budget in a native register: leaf-frame runtime comparison

Rejected after the paired full-command comparisons. No nine-workflow qualification was run. [Full-command result](../paired-region-budget-leaf-e2e-01/summary.md).

The candidate keeps the budget in x20, saves x19/x20 in a 16-byte frame, and publishes the budget on every exit. Generated regions make no native calls and leave x29/x30 untouched. The baseline is the qualified block-linking build 71c; this candidate is af23.

| Engine / workload | Baseline (s) | Candidate (s) | Median paired change (ms) | Candidate wins |
|---|---:|---:|---:|---:|
| jit:word64-default | 1.717231 | 1.733176 | 15.835 | 1/6 |
| jit:word64-inline8 | 1.090171 | 1.099558 | 9.727 | 0/6 |
| jit:sha1-inline8 | 0.459691 | 0.461243 | 1.552 | 2/6 |
| interpreter:word64-default | 14.669556 | 14.645631 | 68.316 | 2/6 |
| interpreter:sha1-inline8 | 4.844067 | 4.906873 | 76.425 | 2/6 |

All 60 commands pass. Each pair uses identical bytecode and agrees on value, virtual instructions, compiled operation coverage, JIT instruction count, native entry count, and peak guest memory. Order alternates per pair. These are runtime measurements, not complete build/test times; six pairs on a shared host are not confidence intervals.

| Workload | Baseline emitted bytes | Candidate emitted bytes | Native entries, both |
|---|---:|---:|---:|
| jit:word64-default | 894,776 | 919,096 | 72,828,899 |
| jit:word64-inline8 | 942,108 | 967,000 | 35,640,770 |
| jit:sha1-inline8 | 276,820 | 284,496 | 14,128,429 |

Both release VMs are 764,480 bytes. The exporter binary is unchanged. The candidate passes 73 bytecode tests, 23,502 native differential/rejection commands, and 99 launcher checks. The ABI wrapper checks preserved registers and stack position on normal, budget, memory, division, and assertion exits, including maximum-u64 budgets. A six-word assembler oracle verified the new frame encodings; guest execution uses the custom emitter.

[Validation](../jit-region-budget-leaf-validation-01.json).
