pgrust passes the fixed held-out regression guard. All 63 primary commands,
21 independent checks, fifteen edited pairs and 42 artifacts verify. Original
assertions and wrong-edit controls are preserved, and sources are restored.
Corresponding bytecode matches; cross-cycle identity is true.

| Measure | Native Cargo | Baseline b2 | Candidate 0e |
| --- | ---: | ---: | ---: |
| Median edited command, seconds | 0.660 | 0.499 | 0.474 |
| Median child CPU, seconds | 0.607 | 0.489 | 0.465 |

Paired wall changes -5.56%, CPU -5.70%.
The paired wall ratio is 0.944350073, below the original 1.05
regression limit. Median guest execution is 0.0243s baseline
and 0.0167s candidate. The comparison includes frontend/wrapper
changes alongside the native runtime; it does not isolate only native copies.

Native remains eighteen jobs, O0/incremental and default test concurrency;
custom remains four jobs with the recorded per-case MIR/inlining settings.
Admission observed 19.17 GiB against 15.05 GiB required,
0.127 seconds before startup. All seven cases remain
required for aggregate qualification; options stay explicit.
