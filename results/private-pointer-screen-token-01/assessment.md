Pointer promotion is parked off main. The fixed five-edit token screen improved
paired complete-command wall time by **0.34%** and child-tree CPU by **0.34%**,
below the predeclared 10% wall target. No folded/pgrust timing guards, broader
retention run or retiming follow this failure.

All 32 commands passed their expected outcomes: original, deliberately wrong,
five valid cumulative production edits, and restored original, each through
native, retained exporter, candidate exporter and a separate Cargo check.
Every original assertion stayed unchanged; all twelve selected tests matched
native outcomes. Both custom modes executed the identical VM with prepared test
isolation and the same profiles, workers, MIR flags and runtime limits.
The compiler optimization changes bytecode; byte-identical artifacts were not
an appropriate requirement. All sixteen executed artifacts and their catalogs
and selections are preserved, and source restoration was independently checked.

Median edited command times were native 3.091 s, retained 8.374 s, candidate
8.291 s, and Cargo check 0.669 s. Those marginal medians differ from the median
of paired ratios used for the decision. This candidate does not close the
large runtime gap in this compute-heavy suite.

Qualification included 344 Rust tests per profile, sixteen typed Rust fixture
commands, 34 real selected tests and three entropy-controlled diagnostic profiles.
The profiles showed 1.59%/1.18% fewer logical token instructions and 0.17% more
folded instructions. Those counts were diagnostic, not a speed prediction.
Two harness/reporting failures are preserved separately: missing fixture package
and duplicate rendered function names. Neither was a compiler failure.

The implementation remains on `experiment/private-pointer-promotion-20260912`.
Only the recipes and evidence enter main. No type/borrow checks, runtime checks,
VM semantics or production defaults were weakened.
