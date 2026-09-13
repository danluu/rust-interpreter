# Bind automatic tool builds to the selected compiler pin

The custom tool builds bytecode and mir-export. The other two workspace crates
belong to the archived backend, so omitting them is correct. The automatic tool
cache currently hashes its relevant Rust/Cargo source files but omits the
launcher's selected TOOLCHAIN string. Changing that pin without editing Rust
can return the previous compiler's binaries. Explicit immutable tool keys have
a separate reproduction contract and must remain usable.

First run five focused boundary tests with Cargo/capability commands stubbed in
isolated temporary roots. Expect only the selected-toolchain-change test to
fail on the original launcher. Then add a versioned cache-key prefix containing
the selected toolchain string and rerun the complete root harness:133 registered
tests, including10 existing compiler-dependent skips. Preserve before/after
source/log hashes and the expected failing regression. No guest runtime, checking
policy, backend, worker setting, or completed performance result changes.
This binds the selected toolchain identifier; it is not a new full environment
fingerprint or a measured compilation speedup.

Use the shared lock,45-second admission and8GiB floor. No host compiler build
is needed for a source-key behavior fix. Preserve old immutable cache entries,
other sessions and the paused goal. Merge the verified fix to main and continue
the full original pgrust SQL-parser support probe.
