# Qualify the selected three-part runtime composition

Select the exact composition inspected in the completed third census: guarded
local-value retention, exact static facts after forwarded loads, and scalar-copy
address folding through the existing local/guarded memory paths. The unchanged
16/32 MiB parser treatment remains parked. No project identity selects behavior.

Enable the composition in ordinary VM code and make the same paths the default
for tests. Keep a test-only old-emitter switch solely for saved-code census
reconstruction. Ordinary CLI defaults, instruction/allocation/memory/code bounds,
bytecode format, strict rustc checking and the exporter remain unchanged.

Add focused interpreter/JIT equivalence cases for guarded external writes followed
by local reads, same-frame guard declines, unselected and partial-overlap writes,
both Copy roles, evicted sources and region/call boundaries. Preserve successful
writes before faults. Cover narrow masked constants, full-width local pointers,
rejected narrow local-pointer facts, aliased destinations, physical-register
assignment, finite budgets and persistent/nonpersistent execution. Reuse the
corrected scalar-copy overlap/fault/alignment fixtures from cc17f82d where their
scope still applies. Run the full workspace in debug and release.

Build one immutable candidate VM with the previously qualified b08f39e2 exporter
and wrapper, recording every digest and the exact source composition. Replay the
existing strict 119-command environment/dynamic/closure/cache/edited-Cargo controls
and the relevant runtime fixtures. Reuse previous proof only with exact identity;
do not attribute current main's optional compiler routes to the retained exporter.

Before timing, run the three saved real-test profile controls with their recorded
entropy inputs and original assertions. Require exact logical per-PC counts,
memory and outputs, and verify post-execution code maps. Census estimates alone
are not guest correctness. Do not ignore a resource error or wrong output.

Then freeze a fresh 40-command token-first changed-source screen with the same
native, baseline A/A, candidate and historical-anchor roles as the existing
guarded-runtime protocol. Original, wrong, five real edits and restored controls
remain mandatory; only the valid edits supply timings. Use the current qualified
runtime as baseline, not the older baseline embedded in the historical driver.
No remaining project performance guards start unless the primary passes its
predeclared wall/noise and CPU criteria. A passing screen only admits the full
multi-cycle comparison and every existing project guard, including private rg-aot
and Nushell. The separate complete parser compatibility target remains required.

Continue manual work with the goal paused. Use the shared lock, 45-second
admission, two Cargo workers and conservative recorded disk floors. Do not
signal other workloads, spawn subagents or activate any AWS offering.
