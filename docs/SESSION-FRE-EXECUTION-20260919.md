# Remaining fre execution cost after the failed session guard

The [complete fre guard](../results/session-project-edit-token-01/summary.json)
failed its unchanged wall gate: candidate/adopted ratio0.97056 plus the0.05575
project A/A allowance exceeds1.0. All176 changed-source commands and strict
rejection controls were correct. This composition remains experimental, and
later guards are stopped. No acceptance timing is repeated.

The [saved cost analysis](../results/session-project-token-costs-01/summary.json)
places median build-to-ready at1.503s and execution at2.439s. The longest test
already starts first and occupies2.367s. These medians are not additive.

A [separate diagnostic replay](../results/session-duration-order-phases-token-02/summary.json)
uses the first cycle and restored artifacts from that exact history, both with
and without template history. All192 original invocations and expected assertion
failures match, with14,878 observed hits and no compilation declines. Median sums
across workers for the five valid edits are:

| Instrumented phase | History off | History on |
| --- | ---: | ---: |
| Ordinary emission |249.505ms|73.394ms|
| Scalar preparation |3.499ms|3.645ms|
| Native publication |9.912ms|9.208ms|

Within cached ordinary emission, median summed key computation is28.867ms,
lookup0.809ms, restoration7.805ms, miss emission34.526ms and capture1.054ms.
Worker intervals overlap and separately computed medians do not sum exactly.
These are instrumented durations, not CPU costs or predicted speedups. Reducing
remaining compilation cannot explain away seconds of guest execution.

The first diagnostic attempt completed one suite before a Python filename
collision broke receipt validation. Its successful prefix and normal owned-server
exit remain closed. The corrected controller starts a new session, including the
initial suite needed to seed process-local scheduling hints. This recovery did
not repeat an end-to-end acceptance sample.

[Two native-PC captures](../results/session-fre-runtime-sampling-01/summary.json)
use the qualified normal candidate VM, original assertions/limits, ordinary
entropy and the exact original artifact shared with the failed guard. Both guests
pass with zero JIT declines. Same-process emitted words are independently
reconstructed before attribution; all generated-code self samples are assigned.

| Generated-code category | Block test | Exhaustive test |
| --- | ---: | ---: |
| Copy |434|228|
| Call transition |351|314|
| Load |202|83|
| Region budget |153|80|
| Flush |118|100|
| Return transition |108|150|
| Scalar bodies |43|92|
| All generated categories |1716|1294|

These partial, perturbed windows identify code locations. They do not measure
latency or retired instructions. Host and post-execution samples remain separate;
scalar-body samples do not identify individual instructions. The capture executes
one selected fresh guest at a time, so session-history and two-worker effects
remain represented by the complete changed-source guard, not these samples.

Next reconstruct the Copy/Load/Store subparts in the saved bytes using the existing
test-only emitter observer. Distinguish address selection, validation, frame-base
calculation, transfers and register publication before choosing another runtime
change. Preserve previous rejected budget, address, spill and scalar candidates;
the operation-level distribution alone is not evidence to retry them.
