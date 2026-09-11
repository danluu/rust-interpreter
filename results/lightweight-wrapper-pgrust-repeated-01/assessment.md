# Pgrust repeated API edits improve with the lightweight wrapper

Fifteen cycles of the same public hash-input API edit verify 135 primary
commands, 45 independent checks and 90 matching paired bytecode snapshots.
All four original tests pass after every correct edit; every wrong edit is
rejected. Source restoration and all frozen inputs verify. Original, wrong-edit
and API-edit bytecode each remain identical across the fifteen cycles.

| Edited command | Native | Heavy wrapper, 78 | Lightweight wrapper, c341 |
| --- | ---: | ---: | ---: |
| Median wall | 0.663535 s | 0.499271 s | 0.479477 s |
| Median child CPU | 0.633732 s | 0.489815 s | 0.470222 s |

The median within-cycle candidate/baseline ratio is 0.9543147002 for wall
time (4.57% lower) and 0.9554182928 for child CPU (4.46% lower). Median paired
differences are −0.022773 s wall and −0.021767 s CPU. All fifteen paired wall
differences are negative, ranging from −0.030167 to −0.004982 s. The independent
edited Cargo-check median is 0.389593 s; it runs no tests and is not a strict
lower bound or an isolated exporter-cost measurement.

Both custom modes use the same VM binary and ordinary JIT, with identical
leaf-inlining settings and resumable/persistent calls disabled. The native
control uses root O0/incremental, eighteen build jobs and default test
concurrency; custom builds use four jobs. Each edited position occurs five
times per mode. The results describe one API edit on this shared host;
qualification and initial cold observations are excluded from warm medians.

This completes the small-project warm comparison in the predeclared
[pipeline experiment](../../benchmarks/experiments/compiler-pipeline/REPEATED.md).
The fifteen-cycle Nushell comparison and six balanced fresh-target cold runs
remain required before deciding retention. In particular, the first Nushell
qualification was slower with the candidate. The earlier native-call runtime
gates remain separate and failed.

[Raw summary](summary.json) · [Verification](verification.json)
