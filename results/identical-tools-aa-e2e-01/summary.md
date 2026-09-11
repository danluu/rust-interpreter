# Identical-tool calibration with real Rust edits

Both compared builds contain byte-for-byte identical VM and MIR-exporter executables. Every pair executes identical bytecode after the same real production edit and runs the same original tests. These are edited builds with separate warm dependency caches; no unchanged-build timing is used as optimization evidence.

All fifteen pairs pass their selected tests, every mode rejects the deliberately wrong production edit, and all three source checkouts are restored. Artifact and installed-binary hashes were rechecked. The explicit retained-candidate selector is also verified: the working-tree exporter differs from the selected identical tools.

| Workflow | Nominal candidate wins | Median paired change (ms) | Range (ms) | Median Cargo change (ms) | Median execution change (ms) |
|---|---:|---:|---:|---:|---:|
| [fre-word64-inline8](../e2e-aa-identical-tools-fre-word64-inline8-01/summary.md) | 3/5 | -9.785 | -42.817 to +836.734 | -6.280 | -2.837 |
| [ruff](../e2e-aa-identical-tools-ruff-01/summary.md) | 3/5 | -16.849 | -162.069 to +311.607 | -16.958 | -1.078 |
| [nushell-type-relations](../e2e-aa-identical-tools-nushell-type-relations-01/summary.md) | 3/5 | -723.998 | -2071.614 to +2136.594 | -707.020 | -0.629 |

Negative changes favor the nominal candidate. There is no compiler or runtime implementation difference to credit for these changes. Stage medians need not add to the command median.

All individual command changes are retained below, including outliers:

| Workflow | Edit | Command change (ms) | Cargo change (ms) | Execution change (ms) | Other command change (ms) |
|---|---:|---:|---:|---:|---:|
| fre-word64-inline8 | 1 | -9.785 | -6.280 | -4.433 | +0.928 |
| fre-word64-inline8 | 2 | -15.222 | -11.284 | -2.837 | -1.101 |
| fre-word64-inline8 | 3 | +51.516 | +51.003 | +1.183 | -0.670 |
| fre-word64-inline8 | 4 | -42.817 | -31.168 | -10.610 | -1.038 |
| fre-word64-inline8 | 5 | +836.734 | +663.315 | +4.385 | +169.033 |
| ruff | 1 | +311.607 | +330.436 | +8.775 | -27.604 |
| ruff | 2 | -117.542 | -116.870 | -1.297 | +0.625 |
| ruff | 3 | +152.757 | +141.299 | -1.078 | +12.536 |
| ruff | 4 | -162.069 | -144.218 | -1.363 | -16.489 |
| ruff | 5 | -16.849 | -16.958 | +2.275 | -2.166 |
| nushell-type-relations | 1 | -723.998 | -707.020 | -1.339 | -15.639 |
| nushell-type-relations | 2 | -943.709 | -946.998 | -0.629 | +3.918 |
| nushell-type-relations | 3 | +2136.594 | +2136.048 | -0.009 | +0.555 |
| nushell-type-relations | 4 | -2071.614 | -2038.630 | -5.106 | -27.879 |
| nushell-type-relations | 5 | +1988.141 | +1966.567 | +4.316 | +17.258 |

“Other command” is the per-pair residual after Cargo and execution, including launcher and process overhead. It is not an independently instrumented cause. Each command includes checking, export, launch, JIT construction and execution. Fresh native controls are recorded in the linked workflow reports; downloads and tool/sysroot setup are excluded.

The guarded inlining experiment’s small word64-inline8 command gain (9.203 ms) is comparable to variation observed here with identical tools. Its five-pair result alone is inconclusive. The guard’s Ruff and larger Nushell regressions remain recorded; a separate A/A run cannot establish their cause or make them disappear. These fifteen pairs do not establish a general noise threshold or a confidence interval.

Use this control to require stronger evidence for small changes: retain all complete-command samples, compare execution stages as supporting evidence, and repeat the actual changed-tool comparison where the decision depends on a small or inconsistent effect. Do not subtract these A/A medians from another experiment.

[Guarded twelve-workflow results](../paired-native-medium-leaf-frame-guard-corpus-01/summary.md).
