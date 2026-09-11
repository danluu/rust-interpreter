The fresh Nushell type-relations history passes its held-out regression gate.
All 63 primary commands, 21 independent checks, fifteen edited pairs and 42
executed artifacts verify. Fourteen original tests and the original wrong-edit
controls remain intact; tracked sources are restored. Corresponding artifacts
and all cycle histories match for this workload.

| Measure | Native Cargo | Baseline b2 | Candidate 0e |
| --- | ---: | ---: | ---: |
| Median edited command, seconds | 7.913 | 4.873 | 4.849 |
| Median child CPU, seconds | 20.924 | 7.316 | 7.084 |

The median paired candidate/baseline wall ratio is 0.988017293
(−1.20%); paired child CPU is −2.47%. This passes the unchanged 5% wall guard;
neither wall nor CPU has a flagged regression. The small difference is not a
material speedup claim. Cargo dominates this workload; median execution is
0.0076s baseline and 0.0105s candidate.

Native uses eighteen jobs, O0/incremental and default test concurrency; custom
uses four jobs and checked standard-library MIR. The comparison includes the
candidate's exporter/wrapper changes as well as resumable calls and persistent
registers. It does not isolate only the latest copy change.

The [qualified amendment](../../benchmarks/experiments/resumable-native-calls/COPY-HELDOUTS-RETRY-01.json)
replaces only the interrupted zero-pair history, whose records remain preserved.
The corrected 25.99 GiB admission passed at 30.34 GiB, 0.169 seconds before startup.
Six required held-out cases remain. No default or retention change.
