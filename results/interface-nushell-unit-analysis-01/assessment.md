# Cargo units after real source edits

Parsed 9 verified snapshots from `nushell` / `nushell-generic-list`.
Reported durations can overlap. The table preserves all matching units per command;
a row is not a serial contribution or an isolated speedup opportunity.
Cold and wrong-edit captures, features, duplicates and unblocking IDs are in [summary.json](summary.json).

## native

| Package / target | Features | Median units | Median summed elapsed |
| --- | --- | ---: | ---: |
| nu-command | aegis-password-generator, crossterm, getrandom, js, notify-debouncer-full, open, os, os_pipe, rand, reedline, uu_cp, uu_mkdir, uu_mktemp, uu_mv, uu_touch, uu_uname, uu_whoami, uuid, which | 1 | 6.570 s |
| nu-protocol nu_protocol "lib" (test) | default, os, os_pipe | 1 | 2.030 s |
| nu-protocol | default, os, os_pipe | 1 | 1.850 s |
| nu-protocol | os, os_pipe | 1 | 1.780 s |
| nu-cmd-extra |  | 1 | 1.260 s |
| nu-engine | os | 1 | 1.210 s |
| nu-parser |  | 1 | 1.100 s |
| nu-cli |  | 1 | 0.920 s |
| nu-cmd-lang | os | 1 | 0.910 s |
| nu-test-support | nu-cli, os | 1 | 0.880 s |
| nu-heavy-utils | endian, merge, yaml | 1 | 0.820 s |
| nu-json | linked-hash-map, nu-protocol, preserve_order | 1 | 0.520 s |
| nu-table |  | 1 | 0.510 s |
| nuon |  | 1 | 0.460 s |
| nu-cmd-base |  | 1 | 0.440 s |
| nu-cmd-extra build-script |  | 1 | 0.380 s |
| nu-std |  | 1 | 0.300 s |
| nu-color-config |  | 1 | 0.290 s |
| nu-cmd-extra build-script (run) |  | 1 | 0.180 s |

## baseline

| Package / target | Features | Median units | Median summed elapsed |
| --- | --- | ---: | ---: |
| nu-protocol | os, os_pipe | 1 | 1.770 s |
| nu-protocol (check-test) | default, os, os_pipe | 1 | 1.380 s |
| nu-protocol (check) | default, os, os_pipe | 1 | 1.240 s |
| nu-command (check) | aegis-password-generator, crossterm, getrandom, js, notify-debouncer-full, open, os, os_pipe, rand, reedline, uu_cp, uu_mkdir, uu_mktemp, uu_mv, uu_touch, uu_uname, uu_whoami, uuid, which | 1 | 1.120 s |
| nu-cmd-extra build-script |  | 1 | 0.380 s |
| nu-parser (check) |  | 1 | 0.310 s |
| nu-cli (check) |  | 1 | 0.270 s |
| nu-cmd-extra build-script (run) |  | 1 | 0.250 s |
| nu-cmd-extra (check) |  | 1 | 0.240 s |
| nu-engine (check) | os | 1 | 0.240 s |
| nu-cmd-lang (check) | os | 1 | 0.220 s |
| nu-heavy-utils (check) | endian, merge, yaml | 1 | 0.210 s |
| nu-test-support (check) | nu-cli, os | 1 | 0.210 s |
| nuon (check) |  | 1 | 0.200 s |
| nu-cmd-base (check) |  | 1 | 0.190 s |
| nu-std (check) |  | 1 | 0.180 s |
| nu-json (check) | linked-hash-map, nu-protocol, preserve_order | 1 | 0.160 s |
| nu-table (check) |  | 1 | 0.150 s |
| nu-color-config (check) |  | 1 | 0.130 s |

## candidate

| Package / target | Features | Median units | Median summed elapsed |
| --- | --- | ---: | ---: |
| nu-protocol | os, os_pipe | 1 | 1.990 s |
| nu-protocol (check) | default, os, os_pipe | 1 | 1.420 s |
| nu-protocol (check-test) | default, os, os_pipe | 1 | 1.390 s |
| nu-command (check) | aegis-password-generator, crossterm, getrandom, js, notify-debouncer-full, open, os, os_pipe, rand, reedline, uu_cp, uu_mkdir, uu_mktemp, uu_mv, uu_touch, uu_uname, uu_whoami, uuid, which | 1 | 1.240 s |
| nu-cmd-extra build-script |  | 1 | 0.350 s |
| nu-parser (check) |  | 1 | 0.280 s |
| nu-cli (check) |  | 1 | 0.270 s |
| nu-engine (check) | os | 1 | 0.250 s |
| nu-cmd-extra build-script (run) |  | 1 | 0.240 s |
| nu-cmd-extra (check) |  | 1 | 0.240 s |
| nu-cmd-lang (check) | os | 1 | 0.220 s |
| nu-heavy-utils (check) | endian, merge, yaml | 1 | 0.210 s |
| nu-test-support (check) | nu-cli, os | 1 | 0.190 s |
| nu-json (check) | linked-hash-map, nu-protocol, preserve_order | 1 | 0.170 s |
| nu-table (check) |  | 1 | 0.160 s |
| nuon (check) |  | 1 | 0.160 s |
| nu-cmd-base (check) |  | 1 | 0.140 s |
| nu-color-config (check) |  | 1 | 0.130 s |
| nu-std (check) |  | 1 | 0.130 s |
