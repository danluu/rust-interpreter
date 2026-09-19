# Start previously slow tests earlier

The parser's longest test was last in all ten valid reports from the previous
changed-source comparison. With template history enabled, it ran for a median
203.713 ms after 41.111 ms of preceding work on its worker. The other worker
finished much earlier. This supports testing a generic scheduling change; it does
not predict the resulting command speedup. See the [worker census](SESSION-WORKER-TAIL-20260919.md).

The experimental `jit-session-duration-order` feature learns advisory name/duration
pairs from the most recent complete request. Before retaining them, it checks both
worker records, exact coverage, current names, and finite nonnegative durations.
Malformed, incomplete, duplicate, or oversized observations clear the hints.
Retained vector and string payload is bounded to 4 MiB and 16,384 entries, with a
4,096-byte name limit. Replacement can briefly retain both bounded tables.

The next request runs longer prior tests first. Unknown names receive zero
priority; ties retain original index order. Every current entry runs once, using
its current function ID, fresh guest state, environment, and resource limits.
Final reports retain original indices and canonical order. The scheduler retains
no guest results, validation decisions, code, or guest state.

Five policy controls and an actual native worker-pool control join four existing
server controls. The live control dirties writable guest statics, exercises low
instruction budgets, and checks fresh recovery and exact coverage after reordering.
The first focused attempt had nine passes and one fixture failure: it tried to
write immutable program data. The corrected fixture uses writable tagged statics.
Both attempts are retained. The [corrected focused qualification](../results/session-duration-order-focused-02/summary.json)
passes ten controls in each profile and four with the feature disabled.

The [complete workspace qualification](../results/session-duration-order-qualification-02/summary.json)
includes:

- 679 Rust tests in each profile, with 17 ignored.
- 39 diagnostic controls, 10 feature-off session controls, 31 ordinary-model
  controls, and a default VM build.
- 442 Python passes and 22 skips reused only after matching source and log hashes.
- 48 owned session processes and 92 clients across the retained and new commands.

The original controller stopped on disk admission after both full Rust profiles
passed. Recovery verified their closed logs, fixture receipts, and retained
binaries against the current target, then ran only the four remaining commands.
No passed test command was repeated.

The [real parser replay](../results/session-duration-order-parser-client-01/summary.json)
passed 1,824 invocations and independently regenerated all 19,597 template hits.
It checks expected assertion failures, current limits, canonical outcomes, and
kernel CPU accounting. A separate diagnostic replay passed another 1,824
invocations with 19,964 observed hits. The [independent ordering audit](../results/session-duration-order-evidence-01/summary.json)
reconstructed previous-duration priorities and verified each worker's increasing
ranks and exact coverage for all 16 requests, including the intentionally failing
edit.

The longest test moved from last to first in all ten valid edited diagnostic
reports, becoming the only test on its worker. With history enabled, its median
preceding work fell from 38.811 ms to zero, but its own interval rose from 198.176 ms
to 221.008 ms. The complete worker interval fell from 264.122 ms to 242.255 ms.
History-disabled worker intervals were 327.549 ms and 282.120 ms. These separate
instrumented observations justify an end-to-end screen, not a speedup claim:
worker assignment and cache warmth change with scheduling.

The qualified normal binaries retain literal parameterization and key domain v1;
shared key caching and instrumentation are disabled. Compiler, exporter, and
wrapper binaries match the adopted baseline. The 40-command changed-source
primary06 is running. Default behavior remains unchanged, and adoption still
requires the full parser and remaining project guards.
