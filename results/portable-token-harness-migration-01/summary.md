The original token-phrase workflow is now runnable through the tracked
`bench_e2e_workflow.py`, `workflow_cases.py` and `interpreter.py`. The harness
accepts an explicit allocation limit, validates its range, forwards it to each
custom engine and verifies the launcher's reported limit. Other workflows keep
their previous default behavior.

A fresh validation completed 21 commands: native and both immutable custom
builds on the cold state, wrong edit and five actual production edits. All seven
candidate and seven baseline bytecode artifacts match the previous workflow
exactly. Test selection, assertions, case hash and edited source hashes match;
the wrong edit is rejected and the owned fre checkout is restored.

This is a harness migration, not a new VM optimization. The fresh marginal
edited-command medians are 2.003 s native, 6.856 s preceding engine and 6.668 s
retained engine. Cold commands are 7.146 / 10.937 / 11.514 s respectively. All
individual observations remain in the [complete run](../paired-portable-token-harness-01/summary.md).
These five different edits remain a small descriptive sample.

[Reproduction command and control settings](../../benchmarks/TOKEN-PHRASE.md).
Build caches and immutable binaries remain local; the benchmark no longer
requires the previously untracked token case or launcher copies. The next
methodology change should repeat actual edits, retain CPU and wall time, and
compare explicit native configurations. It must not substitute unchanged builds
for edited-build measurements.
