Ruff passes the fixed held-out wall regression guard. All 63 primary commands,
21 independent checks, fifteen edited pairs and 42 artifacts verify. Original
tests and wrong-edit controls pass their checks; source restoration and both
paired and cross-cycle artifact identities verify.

| Measure | Native Cargo | Baseline b2 | Candidate 0e |
| --- | ---: | ---: | ---: |
| Median edited command, seconds | 5.104 | 2.730 | 2.767 |
| Median child CPU, seconds | 7.399 | 2.691 | 2.718 |

The median within-edit candidate/baseline wall ratio is 0.991609695
(−0.84%); paired child CPU is +0.58%. Both are below the 5% reporting thresholds.
The marginal candidate median is slightly higher than baseline, while the
median paired wall ratio is lower. These different statistics are preserved;
neither establishes a material speed change.

The candidate remains faster than this native control on the selected batch.
Native uses eighteen jobs, O0/incremental and default test concurrency; custom
uses four jobs and checked standard-library MIR. The candidate includes the
exporter/wrapper changes and resumable/persistent execution. This comparison
does not isolate only native copies and does not qualify whole-project tests.

The first preflight encountered an occupied benchmark lock before checking
space; it started no benchmark and the unrelated process was left untouched.
The second preflight passed at 24.04 GiB against 16.16 GiB required, 0.100 seconds
before startup. No extra timing history was run. Five held-out cases remain;
no retention or default change.
