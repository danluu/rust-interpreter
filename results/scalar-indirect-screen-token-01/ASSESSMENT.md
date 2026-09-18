# Park the indirect/scalar runtime composition

All40 original full-token commands pass their expected assertion outcomes,
including the wrong edit and restoration. All12 tests are unchanged.
Candidate/control bytecode and catalogs match for every source state.

Across five valid edited pairs, median candidate/baseline wall is1.00299236
(0.30% slower), CPU0.99040808 (0.96% lower), A/A wall envelope3.3793%, CPU2.0726%.
CPU conditions pass; the required wall improvement does not. The candidate is
1.6063x ordinary native on this selected suite. Initial builds, wrong edits and
restoration are excluded from the performance ratios.

Descriptive paired stage medians: Cargo+18.60 ms, build-to-ready+20.24 ms,
execution−54.32 ms. These nested observations are not additive and do not replace
the complete-command gate. Exact profiles demonstrate the intended transition
mechanism, not a robust edit-loop improvement. Closure verifies1671 evidence
files and56 artifacts. Preserve this failed result with earlier indirect screens;
no retiming of this unchanged candidate or larger project/parser comparisons.
Main retains adopted df4006e0 / VM6ac4dd9e.

Next review JIT preparation dependencies and costs. The existing body-identity
and immediate-churn censuses already show why an exact-body persistent cache has
substantial invalidation. Do not repeat those censuses or normalize numeric
immediates as pointers. A narrower preparation-stage measurement can identify
actual repeated work without introducing an unsound cache or changing guest code.
