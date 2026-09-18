# Setup failed before any edited pair or candidate timing

The original native and adopted-baseline commands both passed the selected
exhaustive test. The harness then incorrectly required two active prepared
workers. The runner correctly reported requested_workers=2 and workers=1 for
one selected test. No candidate command or valid edited pair ran, so no
performance gate was evaluated.

The source is restored, both commands and baseline/native artifacts are retained,
and1,596 evidence files verify. Correct the harness to require two requested
workers and min(2, selected tests) active workers, add its protocol control, and
use a fresh run/cache namespace. The candidate, source mutations, Cargo workers
and performance gates remain unchanged. This corrects a setup failure; no old
timing sample will enter the fresh comparison. [Closure](closure.json).
