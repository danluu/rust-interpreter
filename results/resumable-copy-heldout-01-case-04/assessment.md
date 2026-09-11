The fre forward-anchored TLS workflow passes its held-out regression guard.
All 63 primary commands, 21 independent checks, fifteen edited pairs and 42
executed artifacts verify. Original assertions, wrong-edit controls and source
restoration are preserved.

| Measure | Native Cargo | Baseline b2 | Candidate 0e |
| --- | ---: | ---: | ---: |
| Median edited command, seconds | 1.457 | 1.069 | 0.998 |
| Median child CPU, seconds | 1.904 | 1.031 | 0.978 |

Paired wall time changes −6.04%, child CPU −6.00%; the median paired wall ratio
is 0.939648079. Both regression checks pass. Median guest
execution is 0.1754s baseline and 0.1366s candidate. The comparison includes the
candidate's frontend/wrapper as well as its runtime changes.

Corresponding baseline/candidate artifacts match. Cross-cycle bytecode identity
is false and remains reported; these executed original tests do not prove
semantic equivalence of every layout across compiler histories. The workflow
uses the recorded fre MIR/inlining/limit settings and original native controls.
It is a selected batch, not full libtest or actual panic unwinding.

Three required cases remain. No default change or whole-project qualification.
