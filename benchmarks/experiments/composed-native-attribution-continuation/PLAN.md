# Finish attribution from the two original captures

The region reader passed five controls and full byte/span/PC validation of both
retained captures. Its independent closure also preserves the initial failed
analysis. Consume that closure, reuse the already successful block summary,
generate only the missing exhaustive summary, and attribute both captures with
the qualified reader. Do not run any guest, profiler, compiler or timing command.

Freeze this continuation, its inputs and original preparation. Hold the shared
lock with a 12 GiB initial and 8 GiB child floor. Record the one summary child
and both attribution results separately from the failed original analysis.
An independent closer verifies source revisions, capture hashes, summaries,
attribution partitions, original successful guest outcomes and all terminals.
The result is a perturbed diagnostic, not a performance measurement.
