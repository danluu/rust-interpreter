# Fifteen pgrust API-edit cycles with independent workers

All 135 primary commands and 45 independent checks satisfy their expected
outcomes; ninety paired artifacts, eleven frozen inputs, ninety wrapper traces
and exact source restoration verify. The original four tests and wrong-edit
controls remain intact. Every paired result is checked against raw wall/CPU
records. Both custom arms use identical tool78 with ordinary JIT/leaf inlining;
only four/eighteen worker counts differ. Native/check retain eighteen workers,
O0/incremental and default test concurrency.

Median edited wall seconds: native 0.658489, baseline 0.488680,
candidate 0.487628. Median paired ratios are **0.9981098106 wall** and
**0.9996062101 child CPU**. The warm regression/CPU guards pass on this
workload. The small differences do not establish a material worker-count gain.
Nushell and the cold study remain required; no retention decision follows.
Qualification timings and the initial cold anchor are excluded from these
fifteen edited pairs. One API edit is repeated fifteen times, with balanced
mode positions and fresh per-run cache identities.

[Full precision and configuration](assessment.json), [workflow verification](verification.json),
[all raw measurement summaries](summary.json).
