# Changed-source parser primary with an explicitly owned session

The completed API, pipe/socket, actual VM client and launcher checks precede this
comparison. Parser-client01 checks16 real suites/1,824 invocations and17,076 exact
verified hits. These are correctness results, not speedup measurements. Use the
closed installed client with exact adopted exporter/wrapper; no compiler policy
change. Keep the adopted runtime as the ordinary baseline.

Run the same original/wrong/five valid edits/restored sequence against five modes:
native, baseline, duplicate baseline (A/A), session without history and session
with64MiB/worker history. Two Cargo/native/guest workers. Rotate mode order across
the five valid edits so every mode occupies each position once. Both sessions are
explicitly started in the owned project cwd, with verification disabled for timing.
They are shut down by owner EOF and reaped using wait4; no existing process is
signaled. Separate compiler-cache namespaces for every mode, with strict checking
and original assertion/native outcome/artifact identity controls unchanged.

Before the primary, run two untimed strict type/borrow rejection controls in a
separate namespace using the actual session launcher option. Neither may submit
a server request. Record them and restore source before the original state.
Every source mutation uses the existing SourceEdit recovery contract.

Record client-command wall and waited-child CPU. Add each server request's user+
system CPU to its command. At exit reconcile request snapshots with complete
kernel server CPU; charge the remainder plus parent/helper startup and teardown
CPU. Charge all session startup/teardown wall and remaining CPU equally across
the five valid edits. Also publish totals for the complete history. Never count
idle wall time spent waiting for other modes as session execution, double-count
request CPU, or exclude server startup/tails. Require actual server executable
identity, PID, request sequence, current history mode and monotonically bounded
CPU counters in every receipt. No automatic retry after lost/failed responses.

Keep the existing prospective gate: median candidate/baseline changed-command
wall plus the maximum A/A deviation must be<1; median CPU ratio<=1 and ratio plus
CPU A/A deviation<=1.05. If a failed gate has A/A noise>8%, call it unmeasurable.
Report candidate/native, candidate/session-off and session-off/baseline separately.
Preserve every failed attempt; no unchanged retiming or altered threshold.
No adoption until the primary and subsequent project guards pass.

Protocol01 tests seven accounting/scheduling controls before real measurements:
balanced source histories, exact CPU conservation, complete setup charging,
superficial wins rejected by startup/tail cost, worst-pair A/A, session-off
comparison, and failure on missing identity/work/nonfinite or invalid counters.
This stage launches no guest or compiler.

All stages hold root .work/benchmark.lock with45-second admission. Protocol/analysis
floor12GiB, closure8GiB. Primary requires the full24GiB initial reservation and16GiB
cache allowance, then8GiB before each child. Eight closed recent parser caches
measured at most668MB each; even five new caches plus the strict-control cache at
3x that allocation fit the allowance. Do not lower gates as free space changes.
No shared-target cleanup, peer cache/process changes, goal calls or subagents.
