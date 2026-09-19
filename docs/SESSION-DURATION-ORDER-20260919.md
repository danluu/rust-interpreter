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
before diagnostic on disk admission. Its three completed commands are closed and
retained. Qualification02 will verify and reuse them, bind the retained binaries
to target bytes before any new build, and run only the four remaining commands.
Verified actual parser replay and separate diagnostic ordering evidence must
precede a new changed-source primary06.
The shared-key variant is disabled; literal parameterization, key-v1, current
checks and the adopted compiler tools remain. No default change or speedup claim.
