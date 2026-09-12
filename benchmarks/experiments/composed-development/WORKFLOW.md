# Prospective composed selected-suite comparison

Candidate tool 6abc0d2980c1dbe9ee48252dd06f2ab0dbc146072f1f3b5b356b2fb86b309b33
contains the four composed runtime/compiler mechanisms and strict function reuse.
It passed 391 tests in both host profiles, seven exact original recorded tests,
the three original one/two-worker suites and the native/cache fixture checks.
The retained selected-suite tool is
fe9dcae0c86c6df0b6ac629034bab3a291e15e5315f9bfc87f5da9cbb4d0fe6e.

Run token, folded and pgrust once each with `workflows.py`. Use their unchanged
current selections of 12, 18 and 4 original tests. Use three cycles of the existing
five production edits. Each cycle includes original source and the known wrong
production edit; finish by restoring, compiling and executing the original.
The 132 complete commands per case include 15 candidate/baseline edit pairs and
15 same-session baseline/duplicate A/A pairs. No unchanged build is a latency
sample. Every custom route uses prepared execution and exactly two suite workers.
Checking stays strict. Baseline and duplicate use the same retained tool in
independent caches; the candidate alone enables `--function-cache reuse`.

Each mode has its own cache. Run ordinary `cargo test --lib -- --exact NAMES`
with default libtest concurrency as the primary native control. A second native
control sets dev/test debug to line-tables-only. Both retain repository settings
otherwise. All six modes use two Cargo workers, with the reference build-script
optimization setting preserved. Keep a separate Cargo-check floor. Copy the
exact guest MIR flags and resource limits from the qualified reference report.
Use ordinary OS entropy, no replay library. Verify every original assertion and
match the selected outcomes, including failures, across all execution routes.

Custom orders follow the existing three-cycle balanced permutation schedule.
Native/default and native/line-table orders alternate around the custom group;
check runs last. The immutable plan stores tool/source hashes and all settings.
Keep all pairs, raw output, launch stages, CPU and storage records. Preserve
bytecode/catalog/selection snapshots by content hash so identical repeated
states do not occupy duplicate files. A/A artifacts and catalogs must match
exactly. Candidate inlining can legitimately change bytecode and function IDs.

For each of the five distinct edits, take the median A/A wall and CPU ratios
across its three cycles. The largest absolute departure from 1 is the descriptive
A/A envelope. It is not a confidence interval. If wall exceeds 4% or CPU exceeds
3%, the run is inconclusive; do not rerun the same candidate seeking acceptance.
Otherwise require at least 8% median paired token whole-command wall improvement
and CPU ratio at most 1+max(1%, observed A/A CPU envelope). Folded and pgrust permit
at most 5% median paired wall and CPU regression. Report paired ratios to both
native controls regardless of the custom gate. Native suite duration comes from
rounded libtest output; its wall residual includes Cargo and process overhead
and must not be called pure compilation time.

Admission is 9 GiB for fre or 4.5 GiB for the small pgrust case, then at least 3 GiB
before every child. The fre allowance covers six compiler caches, content-bound
artifact snapshots and the reserve. Check disk on every command, stop before
starting a child below its floor, retain partial evidence and restore source.
No automatic cleanup/retry or partial-pair splicing. Unrelated workloads remain
untouched. If storage recovery is necessary, it is an explicit separate step.

This comparison fixes scheduling and current selection on both sides. It does
not replace the separate 9637b0ac historical-anchor comparison on the original
three-test token selection. That older VM has no prepared/isolated suite API;
its comparison must use the original ordinary batch interface on both sides
and freeze a separate manifest before timing. Full adoption also requires that
anchor comparison and broader held-outs; no defaults change from this screen.
