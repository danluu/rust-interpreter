# Original-artifact runtime smoke

All 20 commands pass: eight original-assertion executions and twelve exact
short-budget failures. No JIT function declines. Folded logical counters and
per-PC profiles are identical between the integrated and candidate VMs. Each
token profile reconciles its own actual random path, with identical program
metadata and original entropy retained. The same immutable bytecode is used.

This qualifies the runtime initialization change on the two original workloads;
it does not yet exercise new compiler output or measure an end-to-end speedup.
