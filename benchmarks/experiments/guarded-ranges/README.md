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

The four-case prefix completes594 commands and passes all four gates. Nushell
was refused before any case command; its qualified continuation adds only the
remaining132 commands. The continuation source and five-test qualification are
on the same experimental branch under `benchmarks/experiments/guarded-ranges-admission`.
[Prefix and admission](../../../results/guarded-ranges-full-03-admission/assessment.md),
[owned public-cache retirement](../../../results/guarded-ranges-public-cache-retirement-02/assessment.md).
