# Isolate custom Cargo worker count

This follows the [verified wrapper futility decision](../../../results/lightweight-wrapper-cold-futility-01/assessment.md).
Four completed cold histories make its original 5% gate unreachable for any
possible final two results. Its six-history protocol is explicitly incomplete;
the warm results remain reported and the wrapper stays experimental. The worker
experiment starts after that assessment and completed archival, with no changes
to the wrapper's measured inputs. This addresses suggestions 4.5 and 2.1.

The [historical timelines](../../../results/compiler-cold-concurrency-01/assessment.md)
show substantial overlapping custom cold work and CPU/wall about 3.1 under four
jobs, versus about 1.5 after the generic API edit. Native uses eighteen workers.
The measured intervals do not expose ready queues or establish the speedup from
more workers. Compare actual edit/build/test commands, including export and guest
execution. Keep native eighteen-job/O0/incremental/default-thread controls.

Use the existing `78e60cdd` tool in both custom arms, with ordinary JIT, matched
leaf inlining and no resumable/persistent/tree/stub options. Its wrapper/exporter
is the established baseline of the preceding comparison. Do not fold c341 routing
into this experiment, regardless of that experiment's result. Baseline gets four
Cargo jobs; candidate gets eighteen. Compiler, std-MIR, flags, source states,
test selections, budgets and artifact requirements are otherwise identical.
No tool rebuild or guest-runtime change is needed.

The launcher already accepts bounded `--jobs`; the workflow harness currently
uses one value for both custom arms. Add explicit `--baseline-jobs` and
`--candidate-jobs` overrides restricted to paired comparisons. Preserve `--jobs`
as the shared default and existing native/check default behavior. Record the
resolved counts per custom mode and verify every executed launcher command.
Existing reports without overrides must retain their previous interpretation.
Reject invalid, duplicate or contradictory settings before creating a run or
changing source. Cover explicit/default counts, non-comparison misuse, tampered
receipts and historical report verification. Do not weaken artifact checks when
parallel compilation changes allocation order.

First qualify a three-cycle pgrust generic API history starting in reversed mode
order, then a one-cycle Nushell generic API history. Verify original assertions,
wrong-edit failures, mode order, exactly restored source, frozen inputs and
identical corresponding artifacts. If these fail, investigate before measuring;
exclude qualification timings from adoption criteria.

Primary measurements use the existing pinned API cases: fifteen pgrust cycles,
then fifteen Nushell cycles. Retain every original/wrong/edit/revert state and
independent check. Record wall and child CPU time, all samples and per-command
stages. Report each workflow separately. Corresponding custom artifacts must
match; known differences across distinct cache histories remain visible.

Then use six fresh-target Nushell one-cycle histories with initial mode orders:

1. native,baseline,candidate
2. candidate,baseline,native
3. baseline,candidate,native
4. native,candidate,baseline
5. candidate,native,baseline
6. baseline,native,candidate

Only the original-source cold command of each history enters the cold gate.
Cold excludes installation, downloads and prebuilt std-MIR setup; OS caches are
not cleared. No unrelated work is controlled. Collect all six histories unless
a verified deterministic futility bound proves that every possible completion
fails an existing numerical gate. Publish that bound, preserve observations and
mark the protocol incomplete when stopping; never invent missing timings or
accept early. Do not add trials or choose another worker count after results.
Keep qualification and warm-run cold anchors outside this six-sample statistic.

Before considering eighteen workers preferable on this host, require at least
10% median within-history cold wall reduction, no >5% median paired warm wall
regression on either primary workload, and no >10% median child-CPU increase for
cold or either warm comparison. CPU guards avoid buying a small latency gain
with disproportionate extra work. Report uncertainty and individual samples;
these are engineering thresholds, not claims of statistical significance.

Only after those criteria pass, check held-out Ruff, private rg-aot and original
fre workflows with the existing three-cycle/five-edit corpus cases, exact tests,
wrong controls, flags and budgets. Require matching paired artifacts and no
unresolved >5% median paired wall regression per case. No broad default or
large-codebase readiness claim follows from the primary cases alone. An explicit
worker setting remains host-specific evidence, not proof of a universally optimal
CPU-count policy or the fastest native configuration.

Serialize all work using the benchmark lock. More workers may raise peak memory
and disk pressure; record resource observations without interrupting other work.
Preserve failures, source restoration, completed caches and raw evidence. Use
qualified archival only for separately reviewed, completed owned targets outside
measurements. If higher concurrency produces differing bytecode or correctness
failures, prioritize allocation/relocation identity and lowering correctness;
do not hide them by relaxing equality or changing test selection.

Staged groundwork: `scripts/workflow_jobs.py` resolves independent mode counts,
reads historical/new receipts and checks canonical executed job arguments. Its
[standalone qualification](../../../results/worker-count-helper-01/assessment.md)
passes six configurations, 48 rejections, sixteen parser cases and checks 756
historical commands. The helper is now integrated into the workflow/corpus drivers and receipt
verifier after the wrapper futility assessment. Helper02 also checks namespace
JSON serialization. Actual integration checks and project qualification follow;
no measured wrapper input changed during its completed histories.

Both workflow qualifications now pass: pgrust03cycles in qualification02 verifies
36 commands/eighteen artifacts after a preserved pre-compilation guard rejection;
Nushell01 verifies twelve commands/six artifacts. Its pilot cold wall falls from
61.125s to 30.550s while child CPU rises from 178.047s to 233.596s. These observations
remain outside adoption statistics and do not waive the declared CPU guard.
Before primary timing, exercise the corpus coordinator's positive path with one
small pgrust body-edit case, three cycles/five edits and the same four/eighteen
counts. This tests JSON receipts and actual forwarding that invalid-CLI probes
cannot establish; its timings are also qualification-only.
