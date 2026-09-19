# Start previously slow tests earlier

The saved parser census shows the longest test last in all ten valid reports.
With history enabled it spends a median203.713 ms running after41.111 ms of
preceding test work on its worker. The other worker finishes much earlier.
This supports evaluating generic duration-based scheduling, not a predicted gain.
[Observed queue](SESSION-WORKER-TAIL-20260919.md).

The explicit experimental feature learns only advisory name/duration pairs from
a complete previous request. It validates both worker records, exact coverage,
current names and finite nonnegative durations; malformed, incomplete, duplicate
or oversized observations clear the hints. Retained vector/string payload is
bounded to4MiB and16384entries, with4096bytes/name. Replacing the table can briefly
retain both old and new bounded tables. Unknown names have zero priority; equal
priorities retain original index order. Current function IDs are never borrowed
from the previous request. No guest result, validation, code or state is cached by
this scheduler. Every current entry executes once with its current environment
and limits; final reports retain original indices and canonical order.

Five pure policy controls and an actual native Pool control join four existing
server controls. Focused02 passes10controls per profile plus4with the feature off.
The live control dirties mutable guest statics, exercises low instruction budgets,
and verifies successful fresh recovery and original index coverage under changed
ordering. Focused01's nine passes and one failure are preserved: the new fixture
had attempted to write immutable Program.data;02 fixes only the fixture to use
writable tagged statics. [Focused proof](../results/session-duration-order-focused-02/summary.json).

Full qualification01 passed all679Rust tests/profile with17ignored, then stopped
before diagnostic on disk admission. Its three completed commands were closed and
retained. Qualification02 verified and reused them, bound the retained binaries
to target bytes before any new build, and passed the four remaining commands:
39diagnostic controls,10feature-off session controls,31ordinary models and default
VM build. The combined proof includes442Python passes and22skips through exact
source/log reuse;24new servers46clients plus24retained servers46clients.
[Complete qualification](../results/session-duration-order-qualification-02/summary.json).

The actual parser replay passed1824invocations with19,597template hits independently
regenerated and verified, including expected assertion failures, current limits,
canonical outcomes and kernel CPU accounting. Diagnostic replay also passed1824
invocations, with19,964observed hits. An independent saved-report audit reconstructed
previous-duration priorities and verified each worker's increasing ranks and exact
coverage for all16requests, including the intentionally failing edit.

The longest test moved from last to first in all ten valid edited reports. It was
then the only test on its worker. In history-enabled diagnostic observations, its
median preceding test work fell38.811ms to zero, but its own interval rose198.176ms
to221.008ms; the full worker interval fell264.122ms to242.255ms. History-disabled
worker intervals were327.549ms and282.120ms. These separate instrumented runs
support a new end-to-end screen; they do not establish a command speedup. Worker
assignment and cache warmth change with scheduling.

The shared-key variant is disabled; literal parameterization, key-v1, current
checks and the adopted compiler tools remain. Next install the qualified normal
binaries and run changed-source primary06. No default change or speedup claim.
