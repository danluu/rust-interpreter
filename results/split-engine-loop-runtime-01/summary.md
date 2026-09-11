# Separate host engine loops: controlled runtime screen

The candidate keeps each existing engine/profile specialization in its own host function using an inline-never boundary. The boundary is crossed once per execution, outside the dispatch loop. The custom guest emitter and bytecode format are unchanged.

| Engine / workload | Baseline (s) | Candidate (s) | Median paired change (ms) | Candidate wins |
|---|---:|---:|---:|---:|
| jit:word64-default | 1.729842 | 1.710231 | -13.704 | 5/6 |
| jit:word64-inline8 | 1.098047 | 1.085808 | -15.225 | 5/6 |
| jit:sha1-inline8 | 0.458016 | 0.447632 | -10.384 | 4/6 |
| interpreter:word64-default | 14.548947 | 15.064378 | 556.932 | 0/6 |
| interpreter:sha1-inline8 | 4.779449 | 4.857012 | 88.567 | 0/6 |

Runtime-only measurements include loading bytecode and JIT construction; they are not complete edit/build/test commands.
Six alternating pairs on a shared host; all samples and load readings retained.
Baseline and candidate execute identical bytecode. The exporter source is unchanged, but rebuilding its bytecode dependency changed its binary hash.

All 60 commands return the same value and agree on instruction counts, native-entry counts, compiled coverage, and peak guest memory. Interpreter controls use the same two VM binaries.

| Workload | Baseline construction (ms) | Candidate construction (ms) | Baseline code (bytes) | Candidate code (bytes) |
|---|---:|---:|---:|---:|
| word64-default | 3.144 | 3.141 | 894776 | 894776 |
| word64-inline8 | 3.330 | 3.400 | 942108 | 942108 |
| sha1-inline8 | 1.173 | 1.174 | 276820 | 276820 |

The candidate passes 73 bytecode tests, 71 SIMD commands, 79 audit-artifact commands, 99 launcher checks, and 23,502 native differential/rejection commands. Production qualification is separate.

[Validation](../split-engine-loop-validation-01.json), [raw summary](summary.json).

Candidate rejected: 6/15 complete-command wins and a consistent word64 interpreter regression. The original qualified source and both mutable binaries were restored exactly; all candidate artifacts and raw samples remain.
