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
wrapper binaries match the adopted baseline. The [40-command changed-source screen](../results/cross-program-template-parser-screen-incremental-06/summary.json)
passed, including both strict rejection controls, all original outcomes, artifact
identity, source restoration, and complete session accounting. Its median edited
candidate/adopted wall ratio is 0.93117; adding the maximum A/A deviation of 0.03082
gives 0.96199, below the required 1.0. CPU ratio is 0.91047 and its corresponding
sum is 0.94133. Candidate/native wall ratio remains 1.27188. Thus this screen shows
a 6.9% wall improvement against the adopted custom runtime while still trailing
native Rust on this workload.

The [full three-cycle parser guard](../results/cross-program-template-parser-full-incremental-03/summary.json)
also passed: 110 changed-source commands, two strict rejection controls, and 15
valid edited pairs. Median candidate/adopted wall ratio is 0.92440; its maximum
A/A deviation is 0.04593 and their sum is 0.97032. CPU ratio is 0.90271, with a
corresponding sum of 0.94219. Candidate/native wall ratio is 1.24998. These results
support a 7.6% wall improvement against the adopted interpreter on this workload,
while remaining about 25% slower than native Rust.

A prior full-guard attempt collected no commands: its historical protocol receipt
rejected the changed candidate-selection file. That admission failure is retained.
The same eight accounting controls were qualified against the current selection
before the fresh full run. No performance sample was repeated.

Saved full-history intervals put the candidate's median build-to-ready time at
1,223.803 ms and execution at 267.423 ms. The longest test begins first in all
session reports, with a median 210.638 ms interval; work outside the worker interval
within the server request is 29.520 ms. Compilation-duration sums can overlap, and
medians are not additive. The remaining gap is largely before execution, while the
long test still dominates the guest interval.

The held-out [fre token guard](../results/session-project-edit-token-01/summary.json)
completed 176 changed-source commands and two strict type/borrow rejection controls.
All 12 original test outcomes, intentional failures, artifact identities, source
restoration and session lifecycle accounting passed independent closure. A prior
verified replay passed 192 invocations and regenerated all 14,892 template hits.

Fre failed the predeclared wall gate. Median candidate/adopted wall ratio was
0.97056, with a 0.05575 A/A allowance: their sum, 1.02631, exceeds 1.0. CPU ratio
was 0.97782 and its corresponding sum was 1.02629, passing the CPU guard. The
candidate/native wall ratio was 1.66098. The historical anchor improved substantially
(wall ratio 0.71807), but that does not establish a gain over the adopted runtime.
The project protocol uses the largest deviation among five edit-position medians
across three cycles; the worst individual wall A/A deviation was 13.23%. This
differs from the parser protocol's maximum individual-pair allowance. Neither rule
changed after collection.

[Saved fre costs](../results/session-project-token-costs-01/summary.json) put median
build-to-ready at 1,503.463 ms and execution at 2,439.142 ms, versus 1,500.355 ms
and 2,526.987 ms for the adopted baseline. The longest test already starts first
and occupies 2,367.489 ms. History records a median 1,938 hits, but compilation
intervals still sum to 193.436 ms. These overlapping intervals and nonadditive
medians are diagnostic evidence, not an additional speedup measurement.

This composition is not adopted. Later folded, pgrust, private and Nushell guards
are stopped; the prepared folded replay remains unstarted. The failed timing run
will not be repeated unchanged. Next, the qualified diagnostic binary attributes
the remaining fre execution and preparation costs using retained real artifacts.
