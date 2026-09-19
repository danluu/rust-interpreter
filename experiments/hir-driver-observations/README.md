# Hash-driver output validation

This source component validates the nine stdout records emitted by the unchanged
[options-hash driver](../hir-options-hash/controls/driver.rs). It does not execute
the driver, inspect a compiler, or qualify an application performance result.

The parser requires eight ordered observations and one terminal record. It
rejects duplicate JSON keys, missing or extra records and fields, non-u64 hashes,
incorrect worker counts, and a terminal with the wrong process mode. It repeats
all hash comparisons independently: repeated/restored and untracked contexts
must match, a tracked option must change both hashes, and the tracked lint must
change only the incremental hash. Hashes from different processes are not
compared, since their paths and thread settings differ.

The future runner must separately establish source, executable and loader
identities, exact child ownership, successful exit, and eight actual compiler
contexts in each of exactly two processes. Stdout claims alone establish none of
those facts. The finite-wait component remains in
[hir-driver-deadline](../hir-driver-deadline/README.md).

`test_observations.py` contains synthetic positive and adversarial controls.
They perform no process launch, signal, compiler invocation, or benchmark.

`loader_trace.py` additionally validates the two retained dyld line forms, the
exact driver PID, and every expected private library path. Delayed-load notes
must name a uniquely identified earlier system image. Unexpected diagnostics,
foreign or missing private images, malformed UUIDs, and incomplete streams fail
validation. System libraries retain the declared macOS shared-cache assumption.

Its process readback joins both raw streams to an `owned_driver` receipt, checking
the exact command, environment, mode, stream hashes, successful exit and ordinary
started/terminal wait events. It rejects unresolved identity probes and timeout
or stop handling. This cannot qualify the bytes behind a reported library path;
the enclosing stage must still check its actual static closure and immutable
providers, and prove that precisely two driver processes ran.

The eight pure controls in `test_loader_trace.py` passed; their retained result
and raw output are `loader-controls-01.json` and `loader-controls-01.stderr`.
No real driver or provider probe was executed for these controls.
