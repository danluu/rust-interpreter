# Primary passes; full comparisons are required

The combined native-indirect/readonly-scalar/successor-spill VM passes its fresh
40-command fre token primary against adopted df4006e0. Across five valid source
edits, paired median wall ratio is0.96398368 (3.60% faster) and CPU ratio0.95353329
(4.65% lower). Maximum individual A/A deviations are2.221367% wall and2.115417%
CPU. Wall plus A/A is0.98619735 and CPU plus A/A0.97468746: the unchanged gate
passes. These engineering margins are not confidence intervals.

All12 original tests, wrong-edit failures, restoration, matched within-state
bytecode/catalogs and retained original native executable outcomes pass. The
candidate still takes1.57264575 times ordinary native command wall time. The
three constituent failures stay failures; this is evidence for their newly
qualified composition, not a sum of isolated gains.

Descriptive stage medians show137.30ms lower execution and22.65ms higher Cargo
time. These nested/overlapping timings are not additive or causal attribution.
No profile/entropy instrumentation was used in timed commands. Host queries during
this run report Apple M5 Max, Mac17,7,18 logical CPUs,48GiB RAM and Darwin27.0.0
build26A428. Fresh original-PC profiles replaced historical dynamic references only
after the unchanged adopted VM reproduced the same CPU-feature-query drift.

The closure verifies1,672 evidence files and56 retained artifacts. Before timing,
666 Rust tests/profile,443 Python tests (421 passed,22 declared skips),122 strict/
cache commands, five native-map and nine launcher controls, six exact fresh
profiles and13 screen controls passed. All failed preflights/profiles are retained.

Proceed to26 fresh selected/prepared compatibility commands, then freeze the full
five-project history: token, folded, pgrust, private rg-aot and Nushell, stopping
at the first failed guard. Both full-parser guards remain required for adoption.
None of the primary's pairs becomes a full-comparison pair. Main continues to
use the adopted VM; only the independent std-MIR recovery fix has been published.
