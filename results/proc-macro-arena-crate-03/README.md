# Failed whole-crate compilation

The actual proc_macro crate with Arena03 did not compile against the installed
rustc_literal_escaper library: that dependency was marked rustc_private in the
sysroot, producing 43 E0658 errors. The compiler closed with exit 1; no test
executable ran. The result's arena_tests/interner_tests fields are planned counts,
not executed tests. All original source, commands and diagnostics are preserved.

The fresh successor ../proc-macro-arena-crate-04 builds the real dependency source
as an ordinary library before compiling the unchanged candidate source. It does
not inject a feature override or remove any language checks.
