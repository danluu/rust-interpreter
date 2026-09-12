# Concurrent isolated tests with one JIT owner per worker

Native controls use concurrent libtest execution. Our prepared suite currently
serializes independent test bodies, including the two dominant token tests.
Test a structural workflow change: explicit --suite-workers N (1..64), default1,
for isolated fresh/prepared batches. Cap active workers by the selected count.
Each host worker constructs, uses and drops its own JIT on its creating thread.
Do not add Send/Sync implementations for JIT owners or share mutable guest state.
The immutable validated Program can be borrowed by scoped workers.

Use a shared bounded work index for load balancing. Preserve fresh guest memory,
statics, heap, frames, registers and TLS for every test, even after a failure.
Collect outcomes in catalog order. Report requested/effective workers and the
per-worker code-budget scope. Constructor CPU/durations may overlap; their sum
must not be described as suite wall time. Reject unsupported flag combinations
before execution. Keep one-worker behavior and all runtime limits explicit.

Qualify both batch modes, multiple worker counts, failures, limits, immutable
catalog bindings and preserved reports. Keep seeded differential tests in both
host profiles. Host qualification floor: 4 GiB, with the existing host cache,
two Cargo workers and locked offline dependencies. Expect365 passing workspace
tests in each of debug and release, with one ignored test in each profile.

First compare new one-worker execution with the retained selector VM on the
seven exact recorded per-test inputs and three original prepared suites. Require
identical results, instructions, memory peaks and full entropy consumption.
Then validate original native assertion outcomes under two workers, including
the complete current token/folded/pgrust selections. Do not apply the process-
global entropy shim to concurrent workers: its replay ordering is not a per-test
input assignment. Parallel token runs use ordinary OS entropy and report the
resulting per-test counters; deterministic controls must still match exactly.

Screen exactly two workers against one using the same new VM: six alternating
pairs, original bytecode, original assertions, normal entropy, complete process
wall/CPU including startup and all JIT construction. Require20% median paired
token wall improvement with at most20% CPU increase. Folded and pgrust guards
permit at most max(5% baseline,10ms) median paired wall/CPU increase; the absolute
term prevents a tiny saved pgrust process from defining the whole workflow gate.
Record all samples and worker/test scheduling. No parameter search or retiming
after a failed screen. Defaults remain one worker.

Only a passing screen permits a real source-edit/build/test comparison with
matched native, retained one-worker and candidate controls. Preserve checking,
original assertions, deliberately wrong edits and source restoration. Require
at least8% token complete-command wall improvement and separate guard cases
before considering a concurrency default. Storage admission remains unchanged.
