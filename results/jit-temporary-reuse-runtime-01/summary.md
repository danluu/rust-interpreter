# Scratch-register reuse: controlled runtime screen

The candidate remembers proven virtual-register words in scratch x9/x10 within each native block. It skips redundant loads, retains existing spills, and clears knowledge at block entries, joins, virtual-register redefinitions, and unknown instruction clobbers.

| Engine / workload | Baseline (s) | Candidate (s) | Median paired change (ms) | Candidate wins |
|---|---:|---:|---:|---:|
| jit:word64-default | 1.730596 | 1.714168 | -18.075 | 5/6 |
| jit:word64-inline8 | 1.100805 | 1.097439 | -11.866 | 5/6 |
| jit:sha1-inline8 | 0.468307 | 0.481246 | 14.324 | 1/6 |
| interpreter:word64-default | 14.742942 | 14.968944 | 10.126 | 3/6 |
| interpreter:sha1-inline8 | 4.680432 | 4.827644 | 103.906 | 2/6 |

Runtime-only measurements include loading bytecode and JIT construction; they are not complete edit/build/test commands.
Six alternating pairs on a shared host; all samples and load readings retained.
Baseline and candidate execute identical bytecode; the exporter binary is unchanged.

All 60 commands return the same value and agree on instruction counts, native-entry counts, compiled coverage, and peak guest memory. Interpreter controls use the same two VM binaries.

| Workload | Baseline construction (ms) | Candidate construction (ms) | Baseline code (bytes) | Candidate code (bytes) |
|---|---:|---:|---:|---:|
| word64-default | 3.135 | 3.236 | 894776 | 865680 |
| word64-inline8 | 3.394 | 3.445 | 942108 | 908644 |
| sha1-inline8 | 1.216 | 1.226 | 276820 | 266540 |

The candidate passes 77 bytecode tests, 71 SIMD commands, 79 audit-artifact commands, 99 launcher checks, and 23,502 native differential/rejection commands. Production qualification is separate.

[Validation](../jit-temporary-reuse-validation-01.json), [raw summary](summary.json).

Candidate rejected after the full-command comparison: 6/15 paired wins, including 0/5 on default word64. Sources and mutable binaries were restored to qualified build `0d0d7b90`. Candidate sources, immutable tools, and every raw sample remain available.
