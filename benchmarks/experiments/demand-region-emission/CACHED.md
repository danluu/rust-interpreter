# Cached region preparation and compact fragment metadata

Compute native region bounds and guarded-range plans once, in the original
source order under the same shared four-million-unit range-analysis budget.
Borrow the cached plan during emission. Binary-search the selected leader and
emit only that region, with exactly one entry, resume and internal-entry slot.
Keep the selected PC explicit, reject fragments in the whole-function publisher,
and leave every unresolved non-self successor pointed at its own VM tail.

Requalify all 349 bytecode controls in debug and release. Reassemble the exact
two adopted captures, requiring original words, spans, assertions and full-function
entry addresses after resolving declared edges only. Extend the controls for
repeated out-of-order guarded-region staging and accidental fragment publication.

This changes preparation structure, not guest code or runtime demand policy.
All guard plans now exist before emission: code-size refusal can therefore do
more analysis than eager early refusal, and retaining plans increases storage.
Neither cost is a speedup claim. Measure and bound retained analysis before
implementing demand publication or an end-to-end candidate comparison.
