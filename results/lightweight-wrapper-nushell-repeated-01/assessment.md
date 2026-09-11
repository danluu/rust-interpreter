# Nushell repeated API edits improve with the lightweight wrapper

All fifteen cycles completed: 135 primary commands, 45 independent Cargo checks,
fifteen edited pairs and ninety matching paired bytecode snapshots verify. The
fourteen original tests and every wrong-edit control remain intact. The pinned
source was restored, all ten frozen inputs match, and all ninety custom launch
records name the expected heavy or lightweight compiler wrapper.

| Edited command | Native | Heavy wrapper, 78 | Lightweight wrapper, c341 |
| --- | ---: | ---: | ---: |
| Median wall | 11.971748 s | 5.150214 s | 4.963133 s |
| Median child CPU | 32.325429 s | 7.386477 s | 7.268069 s |

The median within-cycle candidate/baseline wall ratio is **0.9576057956**, a
4.24% reduction. The CPU ratio is **0.9806403085**, a 1.94% reduction. Median
paired differences are −0.214211 s wall and −0.142640 s CPU. All fifteen wall
differences are negative, ranging from −0.594629 to −0.047168 s. CPU differences
range from −0.461938 to +0.023469 s. These are descriptive paired observations,
not a significance claim. The independent edited Cargo-check median is 4.290911 s.

Baseline/candidate median Cargo stages are 5.074684/4.889531 s, while guest
execution is 0.007717/0.007643 s. Both modes use the exact same VM binary and
ordinary JIT, with resumable/persistent calls disabled and matched leaf inlining.
The native control uses root O0/incremental, eighteen build jobs and default
test concurrency; custom builds use four jobs and the same prebuilt std-MIR.

Original and wrong-edit artifacts change after cycle zero exactly as in the
[earlier interface run](../interface-nushell-repeated-01/assessment.md); the
generic-edit artifact stays identical. Every corresponding engine pair matches.
The [additional literal occurrence](../interface-nushell-literal-history-01/assessment.md)
narrows that history investigation but is not an equivalence proof. Do not
normalize the artifacts or assume arbitrary cache histories are interchangeable.

This run's initial cold commands take 42.222696 s native, 64.436825 s baseline
and 64.102371 s candidate. That single candidate observation is about 0.52%
lower; it is excluded from the predeclared six-run cold gate. Cold excludes
tool/dependency installation, prebuilt std-MIR setup and OS cache clearing.

Together with [pgrust](../lightweight-wrapper-pgrust-repeated-01/assessment.md),
the warm comparison verifies 360 commands, thirty edited pairs and 180 artifacts.
Neither workload exceeds the five-percent paired warm regression guard.
The six balanced fresh-target cold runs and, if primary criteria hold, held-out
checks remain required before retention. Earlier native-call gates stay separate
and failed.

[Complete records](summary.json) · [Verification](verification.json)
