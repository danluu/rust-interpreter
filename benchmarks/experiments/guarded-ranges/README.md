# Experimental guarded ranges

This directory records a qualified prototype and its prospective comparison.
Main retains the previously adopted VM: the guarded execution change is not
adopted by its passing primary screen. All five full cases remain required.

The exact compiled runtime source is
[e4da187](https://github.com/danluu/rust-interpreter/tree/e4da1878fc4e2e4ad04e1884549464a98e9d60a4),
and the evolving qualification/full-comparison harness is on
[experiment/guarded-ranges-20260913](https://github.com/danluu/rust-interpreter/tree/experiment/guarded-ranges-20260913/benchmarks/experiments/guarded-ranges).
These reports retain original failures and zero-guest offline repairs.
No completed measurement was repeated to cross a performance gate.

[Qualification](../../../results/guarded-ranges-validation-repair-01/assessment.md),
[screen](../../../results/guarded-ranges-screen-token-01/assessment.md),
[full protocol](FULL.md).
