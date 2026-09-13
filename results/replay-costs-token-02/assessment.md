# MIR context, not immediate indexing, dominates replay setup

The refined observer passes75 exporter tests per profile, six diagnostic
harness checks,26 real Cargo fixture commands and16 disabled/enabled token
history commands. All current12-test artifacts, catalogs and expected outcomes
match the retained comparison; strict errors and source restoration pass.
The VM and wrapper remain byte-identical to the adopted tool.

| Five valid edited states, diagnostic medians | Time |
| --- | ---: |
| Current-context preparation, including instance-MIR lookup |93.32ms|
| Immediate scan and index |4.83ms|
| Setup total (contains both rows above) |98.32ms|
| Event resolution and graph/allocation effects |28.15ms|
| Call/frame-observation patching |1.15ms|
| Unassigned destruction/bookkeeping |0.80ms|
| Enclosing binding |128.06ms|

The nested intervals reconcile per command; independent medians need not add
exactly. These instrumented observations are not a new end-to-end speedup
measurement. The extra checkpoint resolves the first observer's ambiguous
setup interval without changing bytecode, caching semantics or checking.

Park the proposed positions-table format rewrite: it targets about5ms of
indexing, not the previously suspected100ms. A future lazy-MIR candidate must
show avoided queries, not merely move their cost from setup to event handling.
Calls and most value bindings require current MIR; strict checking and compiler
dependency validation remain mandatory. No additional observer refinement is
queued without a distinct implementation decision that needs it.

The runtime follow-up is constant-operand emission in the sampled hot regions.
Rotates already execute natively, but even known shift/rotate amounts take the
general register-count sequence. Inspect and qualify direct immediate forms
with exact width/masking/overflow behavior before a primary-first source-edit
screen. This addresses emitted instruction volume without another arena or
allocator redesign. Existing local forwarding and larger-cache experiments
are not repeated.

[Exact observations](summary.json), [edited medians](edited-diagnostic.json),
[current generated-code attribution](../current-runtime-costs-01/assessment.md).
