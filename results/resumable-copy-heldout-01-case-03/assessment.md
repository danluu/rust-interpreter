Nushell's default workflow passes its held-out regression guard. All 63 primary
commands, 21 independent checks, fifteen edited pairs and 42 artifacts verify.
Original assertions and wrong-edit controls are preserved, sources are restored,
and corresponding and cross-cycle artifacts match.

| Measure | Native Cargo | Baseline b2 | Candidate 0e |
| --- | ---: | ---: | ---: |
| Median edited command, seconds | 0.659 | 0.431 | 0.401 |
| Median child CPU, seconds | 0.743 | 0.414 | 0.380 |

Paired wall time changes −6.63%, child CPU −6.70%. The median paired wall ratio
is 0.933748007, below the unchanged 1.05 regression guard.
The improvement is roughly 28 ms per edited command; most time remains in
Cargo. Median execution is 0.0047s baseline and 0.0060s candidate.
This combined-tool comparison includes exporter/wrapper changes; it does not
attribute the improvement solely to the native-copy runtime change.

Native retains eighteen jobs, O0/incremental and default test concurrency;
custom retains four jobs and the recorded per-case options. Admission passed
at 18.76 GiB against 12.65 GiB required, 0.110 seconds before startup. Four held-out
cases remain; no default change or whole-project compatibility claim.
