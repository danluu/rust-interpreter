# Size-tier candidate: qualified, end-to-end comparison pending

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

The unchanged 40-command parser primary is running with two additional strict
rejection controls, separate A/A and session-without-history modes, native Rust,
and complete lifecycle/CPU accounting. It passed the unchanged 24 GiB initial
admission after bounded retirement of owned completed compiler intermediates.
No adoption decision or speedup is claimed. A passing primary must be followed by
the original project regression comparisons, including fre, pgrust, rg-aot and
Nushell. The two earlier session primaries remain failed under their original gates.
