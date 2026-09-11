# Nushell edit timing diagnostic

The repeat passes all fourteen original tests after each of five production edits, rejects the wrong edit and retains identical prior/candidate bytecode. The candidate loses three of five complete-command pairs, with a **+434 ms median paired change**. The original uninstrumented run lost four of five with **+979 ms**. Both runs remain in the evidence; this does not establish the cause of the regression.

Every warm command rebuilds **19 Cargo units**. The selected check-test is the final unit, after another nu-protocol compilation and checks of nu-command and other dependent crates. Its start time accounts for much of the observed difference. Guest execution remains measured in milliseconds. Cargo units can overlap, so their durations must not be summed as elapsed time.

| Edit | Prior command (s) | Candidate (s) | Command change (s) | Selected start change (s) | Selected duration change (s) | Execution change (ms) |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 6.706 | 7.493 | +0.788 | +0.89 | -0.11 | +12.350 |
| 2 | 10.933 | 9.482 | -1.451 | -0.88 | -0.60 | -3.494 |
| 3 | 6.744 | 7.178 | +0.434 | +0.26 | +0.18 | +7.030 |
| 4 | 13.439 | 7.052 | -6.388 | -6.54 | +0.18 | -3.567 |
| 5 | 7.324 | 8.011 | +0.687 | +0.73 | +0.01 | +5.739 |

Native edited commands range from 12.636 to 29.055 seconds in this repeat. The initial native median was 10.180 seconds; this repeat is 20.216 seconds. All observations are retained. Changing host conditions and timing instrumentation limit comparisons between campaigns. The diagnostic enables Cargo timing generation in all modes and includes that work in the timer; it is not a replacement for the original uninstrumented experiment. HTML snapshot copying occurs after the timer.

Cargo reports identify the time spent in build units, but do not establish why an otherwise comparable unit ran slower. The exporter entrypoint and dispatch policy are identical between these two builds. A thin compiler dispatcher may avoid heavy exporter loading for ordinary dependency compilations, but this remains an unmeasured hypothesis. We will not attribute the gap to CPU queries, the JIT, or host contention without further evidence.

Build59 stays an experimental coverage baseline: it adds 61 original passing tests but does not establish a performance improvement. Build07 remains the recorded selected build. The next experiment targets the complete folded-trie workload’s measured 18.9 million interpreted copies, comparing bounded native copies against the same59 baseline.

The earlier attempted diagnostic broad02 was invalidated after a measured script changed. It is excluded from timing conclusions; its logs and artifacts remain preserved. The completed broad03 has 21 retained, hash-verified Cargo HTML reports, complete command records and restored source.

[Original eleven-workflow corpus](../paired-cpu-feature-corpus-01/summary.md), [completed diagnostic run](../e2e-paired-nushell-type-relations-cpu-feature-broad-03/summary.md), [folded-trie profile](../folded-trie-execution-profile-01/summary.md).
