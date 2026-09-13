# Guarded runtime integration is qualified

Tool `c743a75d` combines the exact measured guarded VM `4e9c9af6` with the
qualified main exporter `cccdc909` and wrapper `10fb7656`. Complete current
Rust/Cargo manifests match their qualified sources. The 478 workspace tests per
debug/release profile and 88 exporter/routing tests per profile are reused with
explicit source and executable identity checks; no redundant build was run.

The adapted harness passes 132 checks, with 10 existing compiler tests skipped
in that harness. The new complete tool then passes 263 actual commands:
203 native/cache checks, 20 native/fresh/cached Cargo checks, and 40 real-project
commands. Every project follows original source, a deliberate wrong edit,
five cumulative valid edits, and restoration. All bytecode, catalogs and
original assertion outcomes match the retained reference histories exactly.
Uncalled E0308 and E0499 errors still reject before execution.

The exact VM's seven saved selections, nine suites and three per-PC/memory/
entropy profiles retain their existing qualification. The newer compiler's
196 direct compiler commands and optional observer/query-reuse proofs retain
their own identities. Borrow-check reuse remains off by default. Private source,
name lists and raw records stay local; these published results are aggregates.

The separate 726-command performance campaign passes all five frozen gates.
Token improves wall time by 2.55% and CPU by 1.43% against the prior custom VM,
with a narrow wall pass beyond 2.275% A/A. It still takes 1.773 times ordinary
native on that selection. Other cases pass regression guards without useful
incremental speedup claims. These 263 integration commands establish correctness,
not another timing result, and no completed performance case was repeated.

The qualified runtime and its exact helper changes can now be integrated on
main while preserving the compiler-side work and explicit CLI configuration.
The source-import manifest binds the nine changed source/helper files. All
other Rust and launcher sources already match main. Continue with broader
original parser-test coverage and measured runtime work; do not stop at adoption.

[Component identity](../guarded-ranges-main-compose-01/summary.json),
[harness](../guarded-ranges-main-python-tests-01/summary.json),
[project histories](../guarded-ranges-main-projects-01/summary.json),
[full comparison and limits](../guarded-ranges-admission-resume-01/assessment.md),
[exact source import](source-import.json).
