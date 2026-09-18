# Aggregate Call primary: no demonstrated speedup

The predeclared exhaustive-only changed-source primary completed all 40 commands.
Original assertions, the deliberately wrong edit, source restoration, and
candidate/control bytecode equality all pass. Tool `3081569232` remains experimental
and is parked; main retains adopted tool `df4006e0`.

Five valid edited pairs give candidate/baseline median wall ratio **0.99908220**
and CPU ratio **0.99278538**. The individual A/A envelopes are **0.04742435** wall
and **0.01273368** CPU. The prospective wall gate fails; the CPU conditions pass.
This is not the high-noise (>8%) exception discussed in suggestions.txt. No
unchanged-candidate retry, full comparison, or held-out guard was started.

Median paired stage deltas are Cargo −6.894 ms, build-to-ready −7.552 ms, and
execution +5.110 ms (execution ratio 1.00244335). These nested, descriptive
observations neither add to a causal decomposition nor demonstrate an execution
speedup. The compiler/exporter/wrapper are identical between candidate and
control. Candidate/native median paired wall ratio is 1.80794271 for this exact
selected test; it is not a full-project comparison.

Qualification increased exhaustive scalar Call coverage from 16,298,574 to
21,432,046. That coverage did not translate into an end-to-end benefit. Before
another runtime candidate, inspect costs using retained artifacts, profiles and
emitted code. Separate the newly admitted aggregate bodies from shared ABI
changes; do not infer that either caused the null result. Correctness and coverage
alone do not justify adoption.

The preceding namespace `scalar-aggregate-screen-exhaustive-01` failed during
setup after only the native and baseline cold commands because the harness
misunderstood prepared-worker clamping. It ran no candidate command or edited
pair. Its failure is separately closed and retained. The fixed protocol uses two
requested workers and one active worker for this single-test suite.

[Machine result](summary.json), [stage observations](stage-observations.json),
[closure](closure.json), [prospective protocol](../../benchmarks/experiments/scalar-aggregate-screen/SCREEN.md).
