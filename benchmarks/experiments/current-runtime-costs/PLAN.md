# Current composition cost attribution

The qualified main tool e729a493 has the measured VM99ceabaa. Its existing
memory-operands-profile-01 evidence already provides exact whole-run logical
counts for the current12-test token artifact. Do not rerun those profiles.

Capture one fresh uninstrumented owned-process sample for each dominant token
test: block boundaries first, then exhaustive semantics. Use the exact saved
artifact/corresponding catalog, selected-test VM path, persistent registers,
resumable calls,100billion instruction and150000 allocation limits. Three-second
sample windows with same-process code dumps; existing sample and attribution
tools validate process identity, working directory and executable mapping.
No signals, process-name searches or unrelated process interaction. Sampled
execution is perturbed and cannot support a latency or speedup verdict.

Serialize the two commands, with45-second shared-lock admission and8GiB floor
per command. No other own build/test/profile runs concurrently. Freeze all
runtime source and diagnostic scripts until both commands and analysis finish.
Fail on missing/mismatched evidence; do not rerun to obtain better percentages.

Reuse retained exact profile counters for native entries and rendered
interpreted-operation variants. Native resumable calls/returns occur within
native execution and must not be called VM transitions. Distinguish measured
entry counts, native call counts and interpreted op counts; unavailable exit
causes remain unavailable. No new profile is justified by already available
counts. Same-process samples determine which current paths merit inspection.

The existing classifier identifies exact zero/copy sequences, direct register
array accesses and entry kinds; everything else stays unassigned. Its result
is partial sampled-time attribution, not an emitted-op or retired-instruction
cost model. Inspect map coverage before attempting a typed per-op expansion
table. Do not infer safety facts from rendered opcode text.

Publish compact counters, sample coverage and limitations. Use the result to
choose the next bounded runtime mechanism, alongside the separate124ms binding
observer. Future runtime candidates get primary-first screening; no historical
failed timing result is retried or relabeled.
