# Size-tier candidate: correct, primary unmeasurable

The experimental runtime keeps resumable functions above 65,536 bytecode operations
in the custom interpreter before scalar-callee preparation or native emission.
Smaller reached callees still compile independently. This threshold uses an existing
analysis boundary; it is a compilation-cost heuristic, not proof that all larger
functions exceed native capacity. A compilable large hot function could regress.

The preceding [diagnostic](SESSION-PREPARATION-OBSERVER-20260918.md) found that each
worker repeatedly generated about 14.4 MB of native code for a 140,615-operation
parser function, then discarded it at the remaining code budget. The new candidate
combines early interpretation with the qualified request-cost changes. Instrumentation
is disabled. The compiler, exporter and wrapper match the adopted baseline exactly;
strict type and borrow checking still precede execution.

Qualification source e17e60fb passes 652 Rust tests per debug/release profile, with
16 ignored in each. The exact earlier 442 passing Python tests and 22 skips are
retained because their sources and commands are unchanged. A feature-off VM builds.
The three new qualification commands take 124.2 seconds of setup time, excluded from
steady-state benchmark ratios. All 24 fixture sessions and 46 clients are reaped.

The actual saved-parser replay matches 16 suites and 1,824 original invocations,
including the intentionally wrong source edit's exact failure text. Every restored
native template is independently regenerated: 17,150 verified hits. Kernel server
CPU reconciles with request snapshots. This replay establishes correctness, not
speed. The feature-on VM/server identities and installed compiler composition are
recorded in the closed results below.

- [Qualification](../results/session-large-function-tier-qualification-03/summary.json)
- [Parser replay](../results/session-large-function-tier-parser-client-01/summary.json)
- [Installed composition](../results/session-large-function-tier-install-01/summary.json)

The completed 40-command parser primary is **unmeasurable**, not accepted. All
source states, original outcomes, paired artifacts and restoration match. Both
strict rejection controls returned101 without submitting a session request. Both
servers exited by owner EOF and were reaped; complete kernel CPU and lifecycle
costs are charged under the original protocol.

| Valid-edit paired median | Wall | CPU |
| --- | ---: | ---: |
| Cached session / adopted runtime | 0.921620 | 0.911341 |
| Maximum A/A deviation | 0.088141 | 0.059675 |
| Candidate/adopted plus A/A margin | 1.009761 | 0.971016 |
| Cached / session without history | 0.989230 | 0.974599 |
| Session without history / adopted | 0.961303 | 0.952686 |
| Cached / native Rust | 1.322340 | 1.236810 |

The observed wall reduction is7.8%, below the8.8% A/A allowance. The predeclared
8% high-variance rule classifies this as unmeasurable. CPU meets its gates. Edit4
has a candidate/adopted wall ratio1.11065, so a simple uniform benefit is not
established. These ratios are within-run; they do not isolate the threshold's
effect from earlier measurements. No unchanged retry, larger comparisons or
adoption follows. Inspect retained stage intervals before a materially new choice.

[Primary result](../results/cross-program-template-parser-screen-incremental-03/summary.json).
Source20c3d614 ran10426/10429. The two earlier session primaries remain failed under
their original gates. Correctness proofs remain valid; the experimental runtime
stays on its branch and the adopted runtime is unchanged.

The closed retained-cost inspection reads20valid-edit reports without rerunning any
compiler or guest. Candidate execution median332.9ms; server work outside the worker
interval39.6ms; summed worker setup34.2ms and test compilation98.9ms. The latter sums
overlap across workers and are not CPU or predicted savings. On edit4, candidate
build-to-ready1451.0ms versus baseline1250.4ms accounts for the largest observed
excess; candidate execution371.6ms versus session-fresh372.8ms is similar. Late
edits evict templates, but the median cumulative eviction count is zero; do not
infer absence of eviction from that median. These intervals do not alter the gate.

[Retained-cost inspection](../results/session-size-tier-primary-costs-01/summary.json).
Next add diagnostic-only input and constructor phases to separate reading/hashing,
decoding, catalog validation, structural validation and worker metadata before
choosing a new runtime change. Keep the performance binaries and earlier results.

A later correctness audit found a missing callee register-initialization dependency
in the experimental template key. The recorded suites passed, but those inputs did
not exercise the new reproducer. Further reuse work is suspended until correction
qualification completes. [Reproducer and correction](TEMPLATE-CALLEE-INITIALIZATION-20260918.md).
