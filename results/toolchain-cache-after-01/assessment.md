# Automatic tool cache now follows the selected compiler pin

The automatic launcher previously hashed relevant Rust/Cargo sources but not
its selected TOOLCHAIN string. Changing that pin alone could return the previous
compiler's installed exporter. The retained before-test demonstrates this:
the pin-change regression fails while four cache/reproduction controls pass.

The key now includes a versioned prefix and the selected toolchain identifier.
A changed pin creates a fresh automatic namespace. Existing immutable tool keys
remain valid, and unchanged inputs still reuse verified binaries. The unrelated
function-cache/rustc-dispatch crates belong to the archived backend, so they
correctly remain outside this custom tool's input set.

All 123 runnable root-harness tests pass; 10 existing compiler-dependent tests
remain skipped (133 registered tests). Compilation/capability calls in the five
focused cache tests are stubbed in isolated temporary roots. No host compiler
build or guest command was needed. The original failing test/log/source hashes
are retained. No runtime, checking, worker settings or measured performance
decision changed. This is a selected-pin invalidation fix, not a full build-
environment fingerprint or a compilation-speed claim.

[Before regression](../toolchain-cache-before-01/summary.json),
[after harness](summary.json),
[scope](../../benchmarks/experiments/toolchain-cache/PLAN.md).
