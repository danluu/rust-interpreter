# Current guest work is mostly inside generated code

Two fresh owned executions of the adopted VM pass original assertions, with
same-process samples and uninstrumented code dumps. Existing exact profiles
are reused for whole-run counts; no duplicate profile execution was needed.

| Diagnostic window | Block | Exhaustive |
| --- | ---: | ---: |
| Samples |2199|1708|
| Generated code |92.86%|86.30%|
| Heap inclusive |2.68%|6.56%|
| Native boundary self |2.00%|3.04%|
| Native call/return entry regions |21.51%|30.39%|
| Generated instructions not classified by the existing recognizer |72.49%|54.92%|

These are single perturbed windows, not latency comparisons or speedup
predictions. Call/return entry percentages include their guards and tails;
they are subsets of generated code, not additional disjoint time. The former
40.8% call/return estimate should not govern this runtime. Heap/boundary samples
do not currently justify prioritizing an allocator bridge over generated work.

Exact retained profiles count1,932,198 native entries on block and2,417,740 on
exhaustive. Each equals that test's interpreted-op count. The66.4million and
70.4million resumable calls stay inside native execution; calling all of them
VM transitions would overstate boundary frequency. The exposed counters do not
separately label every exit cause. Allocation/deallocation/reallocation totals
are885,372 on block and1,572,514 on exhaustive; these are operation counts, not
time attribution.

The [ten hottest regions per test](hot-regions.json) resolve every generated
sample to a same-process region. Block's first two regions are SipHash rounds:
110 and80 samples, with3543/1225 emitted words for734/246 guest operations.
The remaining hot block regions include regex determinization. Exhaustive's
hot regions include stable sorting, byte comparison and call entries. Its
sampled call entries can contain188–318 emitted words for one guest Call.
These sizes include guards, wrappers and failure tails and are not dynamic
retired instruction counts. Region boundaries do not establish exact host
instructions per individual bytecode op.

Next inspect proven local-memory traffic in the hot block regions, where
repeated loads/stores and copies are present, and the current call protocol.
A typed bounded census can test whether local value forwarding offers an
actual opportunity without reviving the zero-hit address-check cache. Keep
the bounded binding observer as the next independent exporter diagnostic.
Do not start a reserved-arena or allocator redesign based only on historical
counts. Any implemented runtime candidate gets the new primary-first screen.

[Summary and exact evidence](summary.json),
[prospective diagnostic plan](../../benchmarks/experiments/current-runtime-costs/PLAN.md).
