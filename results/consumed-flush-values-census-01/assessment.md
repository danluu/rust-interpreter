# Flush evidence redirects the optimization toward branch operands

Both saved unprofiled captures reconstruct exactly:1,101/1,305 functions,
25,549/29,731 per-value flush spans, every byte of every flush accounted for.
All409 bytecode tests pass in debug and release. Closure verifies231 distinct
frozen inputs and379 Git bindings. No guest benchmark or code publication runs.

The original consumed-tail hypothesis is small:8/8 of135/180 flush samples.
Most sampled flush work is for a value used by the terminal branch and dead on
all successors:112/157 samples. Live successors account for14/15; unavailable
bounded liveness accounts for1/0. Neither captured profile omits an executed
function. The original eligibility rule remains recorded without modification.

This supports a different, prospective rule for ordinary JIT regions: flush only
values live on a successor. Branch selection still needs its terminal operand,
but exit() reads the unchanged fact table after flush_facts(). The latter does
not discard cached or rematerializable facts; its scratch writes do not clobber
x5/x6 or persistent pairs. A branch operand therefore need not also be written
to the private register array solely for the branch to read it. This must be
qualified with wide branch values, cache pressure, merges/backedges, all budget
boundaries, interpreter fallback and exact original workload outcomes.

Keep the separate native call-tree path conservative: it flushes before an
unexecuted Call tail that may need array-backed ABI operands. If complete CFG
liveness is unavailable, preserve the existing fallback predicate. Do not remove
live-successor stores, guest stores, initialization, checks or budget accounting.

Consumed-only and branch-only spans together cover120/1,651 and165/1,439 generated
samples (7.27%/11.47%). This is a reason to implement and screen the revised
mechanism, not a speedup measurement. Their weighted emitted-word totals are
1,700,632,360/1,952,633,366, not measured retired instructions. Keep scratch-value
forwarding parked for now; this larger mechanism has a simpler correctness proof.

[Attribution](attribution.json), [closure](closure.json),
[qualification](../consumed-flush-values-build-01/summary.json).
