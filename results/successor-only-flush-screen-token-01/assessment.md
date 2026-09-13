# Successor-only flushing passes the primary screen

The fresh 40-command token history passes the preset screen. Five valid source
edits have a median paired candidate/baseline wall ratio of 0.96663 and CPU ratio
of 0.97578: improvements of 3.34% and 2.42%. The same-tool A/A envelopes are
2.09% wall and 2.37% CPU. Ratios with those margins are 0.98756 and 0.99946.
The candidate still takes 1.62991 times ordinary native wall time. These are
complete changed-source build/run commands; initial and restored builds do not
enter the performance ratios.

All original assertions, deliberate wrong edits, bytecode/catalog identities and
source restoration pass. Qualification includes 525 workspace tests in each
profile, 119 strict/cache controls, three exact real workload profiles and 12
screen-harness checks. Two offline emission controls reconstruct the adopted
code exactly and remove only dead-after-exit register flush words. They remove
197,384 and 238,016 bytes from the saved block and exhaustive captures. Smaller
code alone was not used as performance evidence.

The final serialized audit verifies 1,892 distinct frozen inputs, 56 retained
artifacts and 304 Git source bindings. The first protocol admission timed out on
the shared lock before any tests ran; the second admission passed all 12 checks.
Every completed guest command is retained, with no repeated screen command.

This admits further qualification and fresh full histories. Thirteen selected/
prepared correctness commands, the 21 full-protocol checks, all five full
performance gates and the complete original 114-test parser remain required
before adoption. The runtime stays on its experiment branch meanwhile. Stop
before starting the next full case if any performance gate fails.

[Measurements](summary.json), [closure](closure.json),
[prospective full protocol](../../benchmarks/experiments/successor-only-flush-full/FULL.md).
