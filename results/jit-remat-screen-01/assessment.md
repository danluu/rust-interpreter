# Park cross-region rematerialization

The fixed runtime rejection screen fails: median paired wall time regresses
0.78% and CPU 0.81%, against a required 10% wall improvement. All 14 executions
preserve output, exact instruction/peak-memory counts, both recorded entropy
streams and input hashes. Both VMs report zero JIT declines. Candidate code is
14,626,192 bytes versus control 14,643,348; this reduction does not establish a
latency benefit. All pairs, including the later candidate wins, remain recorded.

The candidate passed 315 workspace tests in debug and release (one existing
ignored test). Its uniform-definition and entry-liveness proof preserves initial
zeros; differential fixtures cover high halves, branches, direct/indirect calls,
interpreter exits, code capacities and instruction budgets. Correctness alone
does not justify enabling the optimization. Keep source and build on
`experiment/jit-rematerialization-20260912`; do not merge it or retime it.
The conditional edited-command and broad promotion comparisons are canceled.

The next work is a separate usability foundation: prepared custom JIT code
shared across isolated test executions. Each execution must start with fresh
memory, registers, frames, limits, profiling state and TLS. Establish correctness
and measure a real multi-test command with source edits before claiming developer
latency improvements. This does not reopen any parked optimization.
