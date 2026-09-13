# Integrated reuse observer qualification

The combined source preserves origin/main's compiler-query reuse and adds the
opt-in function-reuse observer. Both exporter and wrapper are rebuilt; the VM
is byte-identical to qualified operation-map runtime83ca5b78. Tool923ad6d9
passes88 exporter/routing Rust tests in each debug/release profile and80 Python
tests, including the ten direct compiler/Cargo suites with196 recorded commands.
Those suites retain positive query-reuse/verify cases and strict error checks.

A fresh28-command observer fixture and16-command fre history also pass. The
new tool with observation off/on matches retained bytecode, catalogs and all
twelve original token test outcomes, including wrong edits and restoration.
These44 commands use the default borrow-cache-off path. Jointly enabling both
diagnostics has no performance qualification.

No performance claim comes from this integration. The original five-edit cost
report remains attributed to its exactdbc221a2 tool; do not substitute timings
from this correctness run. The observer is off by default, and its enabled
work does not change checking, cache keys or query order beyond the tracked
diagnostic option itself. Main's existing query-reuse feature remains opt-in.

The source merge resolved only adjacent module declarations and preserved both
modules. No other session's worktree or process was modified. Runtime scalar
Copy remains experimental because its full adoption guard failed.

[Build and binary identity](../reuse-misses-main-build-01/summary.json),
[observer fixture](../reuse-misses-fixture-03/summary.json),
[real project history](../reuse-misses-token-02/summary.json),
[input and command receipts](summary.json),
[original diagnostic interpretation](../reuse-misses-analysis-01/assessment.md).
