# Stronger native controls

First inspect Cargo's effective test-unit profiles for the pinned fre, pgrust,
Nushell, Ruff and private rg-aot workflows. Manifest inspection already shows
line-tables-only in pgrust/Ruff and unpacked split debuginfo in pgrust. Do not
assume a full-debuginfo baseline. Use Cargo's unit-graph output under the exact
existing O0/incremental overrides; this phase executes no test or compilation.

Compare three specified settings: current repository debuginfo, explicit
line-tables-only/unpacked, and debug=0/unpacked. The debug=0 preset also permits Cargo’s automatic debuginfo stripping, recorded
explicitly by the unit graph; symbol stripping is not enabled. Keep optimization, assertions,
overflow checks, features and target selection unchanged. Collapse identical
effective candidates before timing. Preserve raw private graphs locally and
publish only aggregate profile/count information.

The later timing phase must measure real source edits with original assertions,
retain the actual Cargo command as the main metric, and separately record native
build/test execution. Select a development preset on calibration edits before
confirming on other edits/workflows. Do not select a different fastest preset
post hoc for each reported edit. CPU is reported, and worker settings are explicit.

## Native calibration, fixed before execution

Run fre token-phrase with the three distinct effective presets, one fresh Cargo
target directory each, 18 jobs/default test threads and the existing
O0/incremental plus host-build-O0 controls. Replay original source, the known
wrong production edit and five cumulative real edits. Rotate preset order with
the existing paired workflow schedule. Require original assertions, negative
rejection, actual crate recompilation and exact source restoration. This is
21 complete Cargo commands, including 15 edited commands. No unchanged-build
latency enters the decision.

Choose a preset using edits 1–3 only. A candidate must improve median paired
complete-command wall time by at least 8% over repository settings. Of the
eligible presets choose the fastest, preferring line-tables-only if it is
within 3% of the fastest, to preserve source-line backtraces. Freeze that choice
before edits 4–5. Confirmation requires both remaining wall ratios below 1.0
and their median at most 0.95. CPU is recorded without a CPU veto. Failure is
inconclusive/parked, not an invitation to repeat until it passes. This small
calibration selects a control for further workloads, not a universal default
or a statistical performance guarantee.

For each successful edited Cargo command, parse its rounded native suite time
and Cargo's reported build duration. Then run the exact emitted test executable
again with the same filters and environment, outside the primary timer. Record
that repeat's process wall/CPU time and verify its assertions; do not substitute
it for the first execution or subtract it from the Cargo command. This adds
15 diagnostic repeats and makes the different timing scopes explicit.

Storage admission uses three full historical native-cache unique-file sizes,
20% growth, 16MiB metadata and the existing 8GiB free-space floor. The reference
is the completed budget token native history. Completed scalar-smoke native/
check caches and four compiler incremental subdirectories were deleted after
terminal, exact ownership, open-file and 48 preserved-hash checks; sources,
executed bytecode, diagnostics and raw records remain. No archive was created.
