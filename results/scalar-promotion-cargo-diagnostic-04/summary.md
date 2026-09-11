# Nushell Cargo-unit and child CPU diagnostic

Candidate minus retained after five real production edits. The instrumented run is excluded from performance qualification.

| Edit | Command | Child CPU | Target start | Target duration | Remaining interval |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | +279.4 ms | +105.9 ms | +150.0 ms | +110.0 ms | +19.4 ms |
| 2 | -43.3 ms | -202.3 ms | +140.0 ms | -160.0 ms | -23.3 ms |
| 3 | +238.6 ms | +219.5 ms | +140.0 ms | +100.0 ms | -1.4 ms |
| 4 | +1299.4 ms | +230.5 ms | +1040.0 ms | +250.0 ms | +9.4 ms |
| 5 | -879.9 ms | -400.5 ms | -770.0 ms | -140.0 ms | +30.1 ms |

Target start + target duration + remaining interval partitions each command difference. These are elapsed intervals, not separately measured CPU costs. Stage medians need not add to the median command difference.

| Cargo unit | Baseline duration | Candidate duration | Paired duration change |
| --- | ---: | ---: | ---: |
| nu-protocol | 1.900 s | 2.360 s | +110.0 ms |
| nu-protocol (check) | 1.370 s | 1.560 s | +110.0 ms |
| nu-protocol (check-test) | 1.360 s | 1.470 s | +100.0 ms |
| nu-command (check) | 1.190 s | 1.410 s | +40.0 ms |
| nu-cmd-extra build-script | 0.350 s | 0.310 s | -10.0 ms |
| nu-parser (check) | 0.250 s | 0.250 s | -10.0 ms |
| nu-cli (check) | 0.240 s | 0.240 s | -10.0 ms |
| nu-engine (check) | 0.230 s | 0.220 s | -10.0 ms |
| nu-cmd-extra (check) | 0.210 s | 0.230 s | +10.0 ms |
| nu-cmd-extra build-script (run) | 0.210 s | 0.210 s | +0.0 ms |
| nu-cmd-lang (check) | 0.200 s | 0.190 s | -10.0 ms |
| nu-heavy-utils (check) | 0.180 s | 0.190 s | +0.0 ms |
| nu-test-support (check) | 0.180 s | 0.190 s | +0.0 ms |
| nu-json (check) | 0.150 s | 0.150 s | +0.0 ms |
| nu-table (check) | 0.140 s | 0.140 s | +10.0 ms |
| nuon (check) | 0.130 s | 0.130 s | -10.0 ms |
| nu-cmd-base (check) | 0.120 s | 0.120 s | -10.0 ms |
| nu-color-config (check) | 0.120 s | 0.110 s | -10.0 ms |
| nu-std (check) | 0.110 s | 0.100 s | -10.0 ms |

The instrumented run is excluded from ordinary performance qualification.
Cargo units can overlap; their durations are not additive command costs or a reconstructed critical path.
Cargo HTML timestamps have report precision, typically hundredths of a second.
Child CPU is user plus system RUSAGE_CHILDREN deltas for the entire waited command tree; parallel CPU can exceed wall time.
Child CPU does not identify which individual compiler unit consumed it.
Selected duration minus exporter timers includes post-callback compiler work, wrapper startup/teardown, and timing precision.
An association in these samples does not establish a causal system-level explanation.

A read-only recursive filename search took 8.65 s during candidate cold setup. It is recorded in the observer note and was not repeated during edited samples. The raw cold measurement is retained; this whole run remains an instrumented diagnostic.

In edit4, 1.04 s of the 1.30 s difference is before the selected target starts. Child CPU rises by0.23s while the reported major-fault count rises by51,786. This suggests substantial variation outside the new lowering pass; it does not establish the source of the variation. Root88 remains retained.
