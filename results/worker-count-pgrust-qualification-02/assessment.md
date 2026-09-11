# Pgrust worker-count qualification

All 27 primary commands and nine independent checks satisfy their expected
outcomes, including the original four tests and wrong-edit rejections. All
18 corresponding artifacts match; the pinned source is restored byte-for-byte.
Eleven frozen input hashes and eighteen heavy-exporter traces verify. Both
custom arms use identical tool78 binaries and ordinary JIT with leaf inlining;
baseline uses four workers and candidate eighteen. Native/check retain eighteen
workers, O0/incremental and default test concurrency. Three cycles start in
candidate/baseline/native order and balance edited mode positions.

Median edited wall seconds: native 0.647687, baseline 0.493633,
candidate 0.496516. Median paired candidate/baseline ratio 1.0055983071.
This qualification is excluded from adoption measurements. The initial attempt
was rejected before compilation and is [preserved](../worker-count-pgrust-rejection-01/assessment.md).

[Workflow checks](verification.json), [configuration/source checks](configuration-verification.json),
[full measurements](summary.json).
