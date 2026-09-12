# Persistent reuse misses the first complete-command gate

The one-cycle tokenization screen improves median paired edited wall time by
5.30% and child CPU time by 4.32%. It misses the predeclared 8% wall gate. All
21 primary commands, 7 independent check commands and 14 bytecode comparisons
pass. Test source is unchanged; the wrong production edit fails as expected
and the source is restored. No unchanged build is a performance sample.

The candidate combines persistent function reuse, bulk payload serialization
and the SHA hardware backend, with the retained VM and wrapper. Median complete
command times are 4.835 s for the retained custom tool, 4.667 s for the candidate
and 2.214 s for native. These medians are not the median paired ratio. Cold
original commands are 9.729 s retained, 9.772 s candidate and 7.459 s native,
with tools and standard-library MIR already prepared. This short screen is not
confirmation or a confidence interval.

Per-pair Cargo time falls by roughly 80–298 ms. Guest execution still takes
about 3.1 s in both custom modes and dominates the remaining latency. Exporter
lowering falls from median 832 to 602 ms, while strict frontend time stays near
620 ms. Cached binding still costs roughly 136–147 ms. The remaining inlining
and CFG intervals are only about 47 and 58 ms, so caching either alone cannot
resolve the gap to native. Graph-level reuse would require additional correct
binding and interprocedural dependency machinery, not just persisting final
functions with their old addresses.

Keep this opt-in cache candidate disabled by default. Do not retime it, run its
conditional promotion holdouts, or treat the correctness histories as a passed
performance gate. The cache machinery remains useful for experiments and is
qualified against exact output, semantic edits and failed publication.

Next establish the current merged custom JIT's actual contribution before
building a larger graph cache: this screen deliberately retained the historical
VM to isolate exporter work. Inspect that composition and current execution
profiles, then choose a materially different runtime/compile strategy from the
whole-command costs. Keep the native control and the retained full-workflow
anchor in subsequent comparisons. Fixed frame clearing and scalar ABI retain
their earlier parked decisions.

Exact commands, CPU accounting, five paired ratios, cache counters, source and
artifact hashes are in `summary.json`, `verification.json` and `decision.json`.
