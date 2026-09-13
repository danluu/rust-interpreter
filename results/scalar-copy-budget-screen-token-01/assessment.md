# Scalar Copy plus budget guard: park after the primary screen

All40 commands preserve original assertions, source restoration and identical
candidate/control bytecode and catalogs. The candidate fails its prospective
screen gate: paired wall ratio1.023906 and CPU ratio1.007886, with8.7967% wall
and5.5559% CPU A/A envelopes. There is no established incremental gain.
The full five-case comparison remains unstarted; do not repeat this screen.

| Five valid edited pairs | Ratio |
| --- | ---: |
| Candidate / adopted baseline, wall | 1.023906 |
| Candidate / adopted baseline, CPU | 1.007886 |
| Candidate / fixed anchor, wall | 0.807815 |
| Candidate / ordinary native, wall | 1.847936 |
| Wall ratio plus A/A margin | 1.111873 |
| CPU ratio plus A/A margin | 1.063445 |

The fixed-anchor improvement includes previously adopted work and cannot meet
the incremental gate. Ratios are paired before aggregation. Independent median
command times (candidate4.4071s and baseline4.4346s) do not replace the paired
ratio and must not be used to reverse the failed decision.

The candidate passes456 Rust tests per profile,121 Python checks (ten opt-in
compiler tests separately qualified and skipped in this harness), and222 real
correctness/profile commands. Every guard's cost, branch destination and
restoration instruction matches its typed operation span. Code shrinks3.86%,
3.92% and3.71% across the three profiles. Compared with scalar Copy alone, the
new guards remove exactly one net word per region. Neither static size nor
correctness establishes lower end-to-end time.

An offline stage summary leaves the decision unchanged: execution ratio0.99441
lies inside8.6844% execution A/A, while Cargo ratio1.04841 lies inside13.2377%
Cargo A/A. These intervals do not identify a causal slowdown or establish that
the runtime is faster. Normal entropy and the shared host remain part of the
declared experiment; no command is excluded after seeing its timing.

Retain main's adopted runtime. The next investigation concerns the larger
checked-address sequences used by memory operations: preserve both arenas,
the actual heap tag, complete bounds/null/readonly checks, and fault order.
This is a separate mechanism; the failed Copy/budget changes are not adopted.

[Exact build](../scalar-copy-budget-build-01/summary.json),
[real qualification](../scalar-copy-budget-validation-01/summary.json),
[guard and code evidence](../scalar-copy-budget-profile-01/summary.json),
[unchanged screen verdict](summary.json),
[explanatory stage audit](stage-analysis.json).
