# One declared Ruff infrastructure retry

The original `aggregate-relocation-heldout-01-ruff` is incomplete. Its
[stop assessment](../../../results/aggregate-relocation-ruff-stop-01/assessment.md)
verifies one cycle: 21 primary commands, seven independent checks, five real-edit
pairs and 14 executed artifact snapshots. Original assertions, intentional
wrong-edit failures, immutable tool controls and source restoration verify.
The next cycle reached its original-source transition, then the disk guard
stopped before another compiler child at 7,517,466,624 free bytes.

Admission had observed about 22.01 GiB against a 16.16 GiB requirement, which
already included the 8 GiB running floor. Free space later recovered above
19 GiB and then 23 GiB. This is not evidence that a specific other process caused
the shortage: transient compiler storage, filesystem accounting and shared-volume
activity have not been separated. Do not change another workload or claim that
archival or waiting is a compilation improvement.

Preserve the failed run, its exact sources/receipts and the separate first
assessment schema failure. Exclude its five partial edit pairs from the planned
15-pair gate. Permit **one** distinct fresh history:
`aggregate-relocation-heldout-01-ruff-retry-01`. Reproduce all three cycles and
all original checks. Keep tools, guest flags, native profile/concurrency, runtime
options, edits, assertions, mode rotation and both 5% gates unchanged.

Before starting, qualify a separate coordinator and narrow receipt adapter.
Do not change the frozen original runner, compiler verifiers or failed status.
Bind the retry to this amendment, the verified stop assessment, the exact
original command and unchanged measured inputs. The benchmark command may
differ only in run ID. The following Nushell case must explicitly depend on the
completed Ruff retry. Later cases can retain their original predecessor chain.
Reporting must map actual histories explicitly, preserve the failed original,
and independently recompute all seven case gates without pooling them.

Increase the Ruff retry's live admission reserve by **8 GiB**, making its
minimum about **24.16 GiB**; keep the benchmark's running floor at 8 GiB.
This is extra operating headroom, not a guarantee about shared-volume demand.
Use bounded waiting or separately reviewed eligible caches if necessary.
Record low-frequency free-space observations during the retry through an owned
coordinator monitor, including its start/stop identity and cadence, to investigate
transient demand without changing the measured benchmark sources. Qualify the
monitor's termination and receipt handling. Do not run competing builds/tests.

If the retry has another infrastructure failure, preserve it and reassess the
resource constraint before any further attempt; do not retry until a favorable
timing result appears. A completed performance failure remains a failure.
The production compiler is unchanged, and all seven completed held-outs are
still required before any adoption decision.
