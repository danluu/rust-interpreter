# Cargo compilation profile: nushell / float-ranges

3 actual production edits, followed by the same existing test batch. The first build primes an independent cache and is excluded. These are instrumented diagnostic timings. Compilation units overlap; their durations do not sum to the complete command or its critical path. An unrecompiled unit counts as zero for that edit.

| Package and target | Median compilation seconds |
|---|---:|
| nu-protocol | 1.350 |
| nu-protocol (check-test) | 1.120 |
| nu-protocol (check) | 1.050 |
| nu-command (check) | 0.810 |
| nu-cmd-extra build-script | 0.300 |
| nu-cmd-extra build-script (run) | 0.220 |
| nu-parser (check) | 0.210 |
| nu-cli (check) | 0.200 |
| nu-engine (check) | 0.190 |
| nu-cmd-extra (check) | 0.170 |
| nu-heavy-utils (check) | 0.160 |
| nu-test-support (check) | 0.160 |
| nuon (check) | 0.150 |
| nu-cmd-base (check) | 0.140 |
| nu-cmd-lang (check) | 0.140 |
| nu-json (check) | 0.140 |
| nu-table (check) | 0.120 |
| nu-color-config (check) | 0.110 |
| nu-std (check) | 0.100 |

Complete Cargo timeline reports and exact unit features are retained with the raw records.
