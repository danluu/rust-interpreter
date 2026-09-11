# Fifteen Nushell API-edit cycles with independent workers

All 135 primary commands, 45 independent checks, ninety corresponding artifacts,
eleven frozen inputs and ninety wrapper traces verify. The pinned source is
restored byte-for-byte. The same fourteen original tests and wrong-edit controls
remain intact. Both custom arms use tool78, ordinary JIT and matched leaf
inlining/std-MIR; only four/eighteen Cargo workers differ. Native/check retain
eighteen workers, O0/incremental and default test concurrency.

Median paired wall ratio: **1.0059031510** (+0.5903%).
Median paired child-CPU ratio: **1.0732865843** (+7.3287%).
Both warm guards pass; these observations do not show a warm-build gain.
The six predeclared fresh-target cold histories remain required. No adoption,
early acceptance, threshold change or extra worker setting follows from this run.

| Edited mode | Median wall seconds | Median child CPU seconds |
| --- | ---: | ---: |
| native | 12.366153 | 35.248512 |
| baseline | 5.288239 | 7.996041 |
| candidate | 5.279868 | 8.475667 |

Ratios are medians of paired observations, not ratios of the separate medians
above. All fifteen per-cycle ratios and their minimum/median/maximum remain in
the verifier output. They are engineering observations, not significance claims.
Qualification timings and this run's initial cold anchor are excluded from the
warm statistic and from the separate six-history cold comparison.

Original and wrong-edit bytecode each have two hashes across cycles; the API-edit
artifact is stable. Corresponding baseline/candidate artifacts always match.
This repeats the known cache-history layout discrepancy and does not prove its
cause or cross-history semantic equivalence. No equality requirement was relaxed.

The independent Cargo-check median is 4.392976s. Reported selected-crate
frontend medians are 1.114695s / 1.094443s; total lowering medians are
0.071469s / 0.071840s. Nested optimizer times are not added to lowering. These
separate spans and controls are descriptive; subtracting separate runs would
not establish causal attribution. The allocation trace remains correctness
groundwork, with limited pure-lowering time available on this particular case.

[Full precision and raw-pair checks](worker-verification.json), [workflow controls](verification.json),
[all measurements and stage summaries](summary.json).
