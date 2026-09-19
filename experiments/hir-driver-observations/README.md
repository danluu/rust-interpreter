# Hash-driver stdout validation

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
