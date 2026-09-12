# Nushell native debuginfo calibration

All 88 commands preserve their expected outcomes on fourteen original tests, including wrong edits and compiled restoration. Across fifteen edited pairs, line-tables/repository wall ratio is 0.96145 and CPU ratio is 0.97434.

The observed A/A envelopes are 3.25% wall and 1.72% CPU. A/A variation stays within the declared 4% wall and 3% CPU bounds. This native control has no 8% optimization gate.

| Mode | Edited command median (s) | Child CPU median (s) | Reported suite median (s) | Build and residual median (s) |
| --- | ---: | ---: | ---: | ---: |
| repository | 7.715 | 11.963 | 0.000 | 7.715 |
| duplicate | 7.781 | 11.905 | 0.000 | 7.781 |
| line_tables | 7.536 | 11.798 | 0.000 | 7.536 |
| check | 4.115 | 6.045 | — | — |

Repository and line-tables controls have identical unit graphs after removing only the debuginfo field. Optimization, incremental compilation, assertions, overflow checks and default libtest concurrency match; both use two Cargo workers. Line tables retain source locations but reduce debugger variable/type information.

Each first command used an empty run-specific Cargo target. These single observations are separate from the warm edited pairs; they do not establish a repeatable cold-build gain.

The suite timer is rounded and its residual includes startup and Cargo overhead. Separately computed medians need not add. This calibration contains no custom-engine commands; a later relative-speed claim needs a same-session custom comparison.

[Raw-bound summary](summary.json). All observations are retained; no partial pairs or retries were selected.
