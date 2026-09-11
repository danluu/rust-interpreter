pgrust-sha1-inline8 passes the fixed held-out regression guard. All 63 primary commands,
21 independent checks, fifteen edited pairs and 42 artifacts verify. Original
assertions and wrong-edit controls are preserved, and sources are restored.
Corresponding bytecode matches; cross-cycle identity is true.

| Measure | Native Cargo | Baseline b2 | Candidate 0e |
| --- | ---: | ---: | ---: |
| Median edited command, seconds | 0.755 | 0.748 | 0.645 |
| Median child CPU, seconds | 0.741 | 0.732 | 0.630 |

Paired wall changes -13.70%, CPU -13.84%.
The paired wall ratio is 0.863016270, below the original 1.05
regression limit. Median guest execution is 0.2109s baseline
and 0.1341s candidate. The comparison includes frontend/wrapper
changes alongside the native runtime; it does not isolate only native copies.

Native remains eighteen jobs, O0/incremental and default test concurrency;
custom remains four jobs with the recorded per-case MIR/inlining settings.
Admission observed 19.21 GiB against 15.05 GiB required,
0.131 seconds before startup. All seven cases remain
required for aggregate qualification; options stay explicit.
