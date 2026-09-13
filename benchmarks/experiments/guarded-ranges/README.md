# Guarded related pointer ranges

The runtime passes the complete five-case comparison and separate main-tool
integration qualification. Its compiled VM source is
[e4da187](https://github.com/danluu/rust-interpreter/tree/e4da1878fc4e2e4ad04e1884549464a98e9d60a4).
The historical timing harness is retained at
[f81ac8f](https://github.com/danluu/rust-interpreter/tree/f81ac8f/benchmarks/experiments/guarded-ranges).
The main integration uses the same VM and preserves the newer compiler work.

All original failures, admission refusals and the zero-guest offline profile
repair remain recorded. No completed performance case was repeated to cross a
gate. The primary gain is narrow and the selected project coverage is explicit.

[Full decision](../../../results/guarded-ranges-admission-resume-01/assessment.md),
[integration](../../../results/guarded-ranges-main-qualification-01/assessment.md),
[protocol](FULL.md).
