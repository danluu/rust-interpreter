# Integration-target edit pilot passes

Five cumulative edits to fre's production end-greedy construction function pass
its three unchanged integration tests through native Cargo and the custom JIT.
The deliberately wrong suffix check fails both; independent Cargo check accepts
the well-typed wrong logic. Every measured edited command rebuilt fre-kernels.

| Measure | Native | Custom | Cargo check |
| --- | ---: | ---: | ---: |
| Median edited command | 1.015s | 0.816s | 0.539s |

The median paired custom/native wall ratio is 0.79595 (20.4% faster); child CPU
ratio is 0.58940 (41.1% lower). The fixed 0.90 pilot target passes. All modes use
18 jobs with warm primed caches; native uses O0/incremental, repository full and
unpacked debuginfo, and default test threads. Custom Cargo costs 0.743s at the
median; guest execution costs 0.0094s. This is one cycle on one target, with no
cold or whole-suite claim and no new runtime retention decision.

All 21 commands, 42 output logs, seven executed snapshots and original test
source hashes were checked. After the measured history, a root-launcher probe
exposed stale reuse when source restoration preserved the backup's old mtime.
The five edit measurements remain valid because each required recompilation.
The [restoration regression and fix](../source-restore-after-01/assessment.md)
cover the subsequent original-source command. Historical helper source is
preserved at `3e44055`; measured records are unchanged.

Next compare a compute-heavy integration target, then repeated histories.
[Summary](summary.json) · [Predeclared pilot](../../benchmarks/experiments/test-targets/EDIT.md).
