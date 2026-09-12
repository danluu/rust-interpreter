# Complete-command register-allocation screen

Freeze this recipe before timing. Candidate is `register-allocation-compose-01`
(`10e28086`); control is `suite-profiling-build-02` (`c013f239`). Their VM and
wrapper bytes match. Only the exporter changes. Both passed eighteen typed
fixture commands, including exact whole-artifact allocation checks.
The compiler passed 352 Rust tests/profile. Original and wrong
real-source controls must pass before measured edits are reached.

First run `screen.py --case token --run-id register-allocation-screen-token-01`.
Use all twelve `token_phrase::tests::` tests from pinned fre `e0df0b0`.
Measure the existing five cumulative production-body edits in `workflow_cases.py`:
name literal-finder result, reuse short-count input length, reuse short-span input
length, orient short-route width comparison, and match short-route event bound.
Keep every original assertion and the deliberately incorrect production edit.
The shared source-state generator freezes exact edits and rotates mode order.
Original, wrong, and restored states run outside the five timing pairs.

All modes use two Cargo workers and repository dev/test profiles. Native executes
one process per selected test. Both custom modes use checked MIR, MIR optimization
level 3 and inline scale 8, leaf inlining, prepared test isolation, resumable calls,
persistent registers, 100 billion instructions and 150,000 allocations per test.
Use separate fresh native, check, retained-exporter and candidate-exporter caches.
Record complete-command wall and child-tree CPU, compiler/export/VM stages,
source transitions, selected outcomes, artifact/catalog/selection digests and
actual tools. Every measured command must follow a content change in its cache.
Bytecode register operands change, while PCs and instruction order stay fixed.
After each source state, outside timing, verify that the complete candidate artifact
exactly equals allocation of the control artifact. A mismatch stops the screen.
Register working-memory accounting applies to each resulting artifact.

Advance only if the median of five candidate/control paired wall ratios is at
most 0.90 and the median CPU ratio is at most 1.00. Otherwise park the candidate
without retiming. If it passes, run separate folded and pgrust five-edit guards
with their established filters/profiles/limits; both wall and CPU ratios must be
at most 1.05. These screens alone do not establish broader adoption or retention.

Hold the global lock (45-second bounded wait), admit the fre screen at 9.5 GiB
free and pgrust at 8.3 GiB, and require 8 GiB before every child. Preserve all
raw evidence and restore original source even on failure. A storage or harness
stop is an incomplete screen, never a passing performance result.
