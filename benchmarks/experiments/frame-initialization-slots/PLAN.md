# Follow exact local pointer slots in the initialization diagnostic

The reservation candidate failed its complete source-edit primary and remains
parked. Restore adopted bytecode source fca687eb before this separate diagnostic.
The previous constant-memory initialization proof covered only16/110 and20/100
historical clearing samples. Its explicit omission of pointer facts through local
memory may explain some declines. Measure this gap before any runtime proposal.

Extend the standalone typed analyzer only. Track at most64 exact eight-byte cells
per abstract state, containing either a frame-relative pointer or a truncated
literal. A preceding exact eight-byte Store can establish a cell; a validated
eight-byte Load can recover it. No incoming argument bytes, initial zero values,
sampled pointer values, smaller loads or pointer pointees become provenance.

Writes invalidate every overlapping cell. An unknown write/effect clears all
cells, even when full prior initialization allows that operation. A confined
callee still reads every argument before its exact returned-result write, which
invalidates overlapping cells. Copy and known-size CopyDynamic of at most128
bytes snapshot complete source cells before destination invalidation; partial
cells, unknown addresses and larger copies establish no facts. Preserve memmove
overlap, zero-length behavior and register-output alias order.

Intersect cell facts at CFG joins, retaining only identical facts on every path.
Entry starts empty, including loop backedges. Keep the original frame/op/register/
block/edge/global bounds and count cell scans, cloning and merges against work
and state storage. Exhaustion declines or loses facts conservatively. This is an
entry-at-PC-zero analysis; it does not authorize arbitrary native entry states,
eliding argument address guards, changing padding or leaving frames uninitialized.

Eighteen authored controls include the original ten, the6400-case byte-mask
oracle, local pointer round trips, partial/unknown/callee writes, load widths and
aliases, joins/backedges, overlap copies, truncation, resource limits and a separate
19584-case concrete-byte copy oracle. All are UNRUN. Run debug and release controls
before analyzing the unchanged saved token artifact. Compile the original proof
alongside the extension and report its old eligibility/declines as a comparison;
do not alter the historical analyzer or its results.

Then join eligible typed Call IDs to already closed adopted-runtime clearing
samples, keeping sample windows separate from logical call counts. Reconcile
every sample and call and report regressions from resource bounds explicitly.
Only material coverage warrants a separate runtime contract and qualification.
No guest execution, native-code publication, timing or adoption belongs here.

Before compilation register a source-bound controller and independent closure.
Use the shared target, two Cargo/test workers, shared lock45s, build admission
max(14GiB,8GiB+2*allocated target), analysis12GiB and child8GiB. The shared target
is never cleaned. Preserve private/peer work, closed failures and the paused goal.
