# Saved Nushell Cargo intervals

All45 valid edited custom observations from the completed memory/lookup
composition verify against their original records and Cargo HTML hashes.
Three interval-accounting tests pass. This audit runs no compiler or guest
and reports historical tools f0af2e3e versus f8713aaa, not the current candidate.
The prospective draft plan remains unchanged as part of the frozen evidence.

Candidate medians: Cargo5.260s, reported-unit interval union4.780s, first-to-last
reported span4.790s, internal uncovered gaps0.010s, and combined time outside
the span0.460s. Total time with no reported active unit has median0.469s.
These independently computed medians are nonadditive. All45 enclosing-duration
checks are consistent; no negative differences were hidden or clamped.

Each candidate observation contains19 reported units. Largest individual
reported-label medians include nu-protocol with an empty target label1.720s,
nu-protocol check-test1.270s, nu-protocol check1.230s, and nu-command check1.010s.
Two nu-cmd-extra build-script labels account for0.280s and0.230s individually.
These units overlap; their durations cannot be added to claim a critical path
or CPU cost. An empty target label does not establish a compilation mode.

Most of the previously described Cargo residual is inside other reported
units. The0.469s uncovered component remains unattributed: the two clocks do
not support separating startup from finalization, and this is not measured
fingerprinting cost. The next useful large-project diagnostic is the actual
unit/argument graph and encoding/query costs, especially the three separately
reported nu-protocol roles. Worker-count or parallel-frontend changes still
need their own matched qualification. Pgrust has no saved per-unit captures
in these comparisons, so it receives no invented unit or startup attribution.

[Summary, tool identities and receipt hashes](summary.json),
[prospective accounting contract](../../benchmarks/experiments/cargo-residual/PLAN.md).
