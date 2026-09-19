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

The [memory subparts reconstruction](../results/session-fre-memory-parts-01/summary.json)
is also independently closed. Two offline emitter tests reproduce the complete
saved native words; the attribution reuses qualified partition and ambiguity
controls. No guest executes and no executable code is published.

| Memory subpart | Block test | Exhaustive test |
| --- | ---: | ---: |
| Load data |285|116|
| Address-space selection |179|75|
| Store data |81|40|
| Bounds check |60|29|
| Frame-base calculation |10|4|

Frame-base calculations account for less than1% of all generated-code samples,
so caching the base is parked. Existing failed checked-address and address-bias
candidates already cover several tempting instruction reductions; this evidence
does not justify retrying those unchanged candidates.

The first generic closure attempt rejected the legacy plan's missing
`controller_command` field before modifying evidence. A dedicated independent
auditor verified the actual supervisor command, three completed diagnostic
commands,324 frozen inputs and19 artifacts. No tests or samples were repeated.

A prospective next direction is to combine complementary mechanisms: the earlier
indirect/readonly/spill composition passed the five project histories but narrowly
failed the parser CPU guard, while session history/scheduling passed parser gates
and failed fre. This needs an interaction review, new qualification and fresh
changed-source comparisons. Neither old result predicts a combined speedup or
authorizes runtime adoption.
