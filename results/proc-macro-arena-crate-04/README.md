# Actual proc_macro crate unit tests

All 12 tests passed: nine Arena tests and three actual Interner tests. The crate
uses the full 18-file source closure from the identified compiler, replacing only
arena.rs and symbol.rs with proposal03. Its unmodified files match the installed
nightly's proc_macro source. No substitute bridge, interner or allocation model
was used.

The first whole-crate attempt failed because its installed literal-escaper
dependency was marked rustc_private. This successor compiles the real cached
rustc-literal-escaper 0.0.8 source as an ordinary library using public core. The
proc_macro source, checking flags and test bodies remain unchanged. The complete
failed attempt is retained in ../proc-macro-arena-crate-03.

The dependency compiler, crate compiler and test process all closed successfully
under the canonical workload lock. Source bytes, exact commands, dependency and
compiler digests, raw output and child records are retained. The sole compiler
warning concerns naming multiple requested output types.

This establishes these unit-test outcomes only. A separate Miri run found an
aliasing violation in Arena03's growth path, so this candidate is not qualified
for adoption. No new macro clients, full compiler, application benchmark or
build-time measurement was produced by this run.
