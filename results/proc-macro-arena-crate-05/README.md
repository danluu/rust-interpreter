# Actual proc_macro tests for Arena04

All 13 tests passed in the real proc_macro crate: ten Arena tests, including the
new capacity-state control, and three unchanged Interner tests. The exact source
closure replaces only arena.rs and symbol.rs in the matching original crate.
The real cached literal-escaper dependency is built normally against the pinned
nightly's public core. No feature override, substitute implementation or language
check removal is used.

All three children closed with exit zero under the canonical workload lock.
Exact commands, source/dependency bytes and hashes, raw output and process records
are retained. The compiler warning concerns multiple output names. No compiler
distribution or application benchmark is part of this test.

The separate Miri05 result passes ten actual Arena tests under both aliasing
models. It does not include the Interner tests. Neither result establishes an
application speedup or removes the need for actual bridge/compiler qualification.
