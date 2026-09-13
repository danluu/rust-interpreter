# Checks after preserving newer main routing

The publication merge passes 253 Python tests with 13 skips (240 runnable tests)
under installed Python3.14.7, and 101 exporter/wrapper tests in each Rust profile.
The checked source revision is5c5a6dbf. Its bytecode source matches the previously
qualified implementation, including the ignored offline diagnostic. The newer
main changes add opt-in MonoItem/compiler-argument/diagnostic-source routing;
they preserve the environment/capacity implementation and its default execution
settings. All frozen merged source files verify.

The first post-merge attempt used system Python3.9. Five modules failed to import
`tomllib`;233 tests were reported with13 skips, and no Rust test command started.
That failure is retained. The revised run explicitly requires Python3.11 or
newer and records the actual interpreter identity. It is not a benchmark rerun.

The159 real strict/project commands and114 original parser outcomes remain bound
to immutable tool b08f39e2 and its recorded integration base. These merged source
checks make no new performance claim and do not relabel that tool as a build of
the later source revision. The JIT arena remains16 MiB.
