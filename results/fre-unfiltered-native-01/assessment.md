# Unfiltered fre baseline exposes target and doc-test gaps

The actual `cargo test -p fre-kernels` command failed on the original source.
It passed **382 unit tests and 52 integration tests**, with seven ignored unit
tests. Two doc tests passed; the third failed. Total: 436 passed, one failed,
seven ignored, zero filtered. The controller stopped before either production
edit and restored source; all processes are terminal.

The failed compile-fail doc test expects `E0451`. Rustc rejected its private-field
construction, but this pinned nightly omitted that error code. Rustdoc therefore
correctly reports that the expected diagnostic was missing. Original assertions
and test attributes remain untouched. This is a native baseline incompatibility,
not an engine regression. The 9.615s command duration is failure latency, not a
successful edit-to-suite measurement.

The native library inventory exactly matches all 389 names in the retained
custom replay: 382 passed and seven ignored. But the unfiltered command also
runs **ten integration-test executables containing 52 tests**, plus three doc
tests. Those are outside the custom replay. The historical body result therefore
does not establish whole-crate coverage, even before libtest/thread semantics.

Priority: add explicit Cargo integration-test target selection to the exporter/
launcher, then qualify those actual assertions. Handle doc-test compilation as
a separate rustdoc/compiler workflow with its original expected-error rules.
Keep this baseline failure visible. Do not remove the expected code, skip docs,
or describe a library-only command as the complete suite. Cached JIT and shared
multi-entry exports remain useful, but target selection comes first for this
concrete coverage gap.
