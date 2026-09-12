# Prepared code with isolated test executions

Start from main 367335f, without the parked rematerialization, cache, scalar ABI,
fixed-clear or budget-register candidates. The next deliverable is an API for
running distinct test entries with shared custom JIT code and fresh guest state.
This is groundwork for ordinary Cargo test suites, not a claim that repeated
unchanged builds are faster.

`PreparedJit` borrows one immutable validated Program and owns its custom code,
lazy compilation tables and immutable analysis metadata on the creating thread.
Each execution owns new data/statics, heap, registers, frames, TLS/destructors,
instruction/allocation/depth budgets and native continuation state. No guest
address, profile counter pointer or backing allocation may survive an execution.
Errors discard guest state and leave compiled code usable for another test.
Configuration affecting emitted code is fixed; reject incompatible execution
options. Entry IDs and arguments are checked. Compilation time is reported per
execution; cache bytes/functions describe retained code, and constructor cost
is reported separately. Instrumented execution stays on its existing path.

Keep the one-shot API and CLI behavior. Share the execution implementation
instead of adding another interpreter loop. Qualification must cover multiple
entries and arguments, changed statics and TLS, leaked guest allocations, dirty
register/frame reuse, errors followed by success, budget exhaustion, capacity
declines, invalid options and ordinary interpreter/JIT equivalence. Run all
workspace tests in debug and release before real workload execution.

Next export explicit original test entries and run a real multi-test batch with
each distinct test once, comparing fresh per-test JIT construction with prepared
code in the same command and with the original native assertions. Record test
names, failures, unsupported features and constructor cost. Then measure full
source-edit/build/suite commands with native and Cargo-check controls. Any
performance claim must include all work within the command; no unchanged-build
or repeated-identical-entry microbenchmark serves as developer-latency evidence.
The existing historical three-test batch has weaker failure/state isolation and
is not an interchangeable control for a full test harness.

Fresh statics model independent executions. Ordinary libtest may share process
globals across tests; this API does not by itself reproduce that behavior.
Native checks for isolated entries must use the same per-test isolation, with
ordinary full-suite results reported as a separate control.

This additive API can be retained for correctness and usability after its
qualifications; it does not enable a new default. Promotion to the Cargo runner
requires real test coverage and unchanged one-shot behavior. Preserve original
assertions and strict rustc checking. Use the shared lock with a 45-second wait,
two build workers and the 8 GiB floor. Preserve raw evidence and publish compact
results and qualified changes regularly.

After the three public edited workflows, extend the saved-artifact qualification
to Ruff's six registry tests and Nushell's four parser-keyword tests. Use the
last successful native executable and matching source-state bytecode from each
owned completed history. Verify their identities and modification times. Run
each native test in a separate process, compare old/new ordinary batches, then
fresh/prepared isolated executions under identical recorded entropy. Empty
entropy tapes are valid for deterministic cases. This is additional correctness
coverage; it provides no new end-to-end or timing claim. Keep the 8 GiB floor.
