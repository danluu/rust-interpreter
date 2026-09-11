# Rejected budget-register variant

Rejected after controlled runtime screen; no paired full-command or nine-workflow qualification was run.

This variant held the native instruction budget in x20 and saved x19/x20/x29/x30 on a 32-byte frame. The qualified baseline is 71c; the rejected candidate is 8977.

| Engine / workload | Baseline seconds | Candidate seconds | Median paired change ms | Wins |
|---|---:|---:|---:|---:|
| jit:word64-default | 1.756464 | 1.768709 | 1.814 | 2/6 |
| jit:word64-inline8 | 1.099273 | 1.096123 | 3.791 | 2/6 |
| jit:sha1-inline8 | 0.460719 | 0.456475 | -3.615 | 4/6 |
| interpreter:word64-default | 14.466450 | 14.692846 | 234.758 | 0/6 |
| interpreter:sha1-inline8 | 4.816247 | 4.935449 | 112.880 | 1/6 |

All 60 commands passed, with identical bytecode, virtual instructions, compiled coverage, JIT instruction counts, native entry counts, and peak guest memory. Order alternated per pair. These are runtime measurements on a shared host, not build/test timings or confidence intervals. Every sample is retained. The interpreter regressions have not been attributed to a specific mechanism.

The candidate passed 73 bytecode tests, 23,502 native differential/rejection commands, and 99 launcher checks. A follow-up tests a 16-byte x19/x20-only frame: generated regions do not call native functions or modify x29/x30. That follow-up must earn its own validation and real end-to-end evidence.

[Validation](../jit-region-budget-register-validation-01.json).
