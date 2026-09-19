# Eight actual library integration tests passed

The fixture compiled against an explicitly built Arena04 proc_macro library and
passed all eight tests. Binary dependency information includes that new library
and the real literal-escaper dependency, with no installed proc_macro library.
The original source-only README and review record remain unchanged.

Exact commands, source/library hashes, raw diagnostics, dependency information
and closed process records are in ../../results/proc-macro-arena-bridge-01.
This tests the selected library's real client/dispatcher bridge, not rustc's
internal server or an installed compiler distribution. No performance result
was produced.
