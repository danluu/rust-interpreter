# Current ES8 edited-source comparison

The adopted custom engine is still slower on this compute-heavy integration
target: median paired custom/native is **1.516x wall** and **1.833x child-tree
CPU** over five actual production-source edits. Maximum absolute duplicate/
custom deviation is **1.880% wall**, **0.464% CPU**. Every pair remains in the
summary; no timing retry or candidate/adoption decision occurred.

| Mode | Median edited command wall | Median child-tree CPU |
| --- | ---: | ---: |
| Native | 1.353s | 1.602s |
| Custom | 2.077s | 2.943s |
| Identical custom duplicate | 2.062s | 2.935s |
| Cargo check | 0.531s | 0.515s |

Paired ratios are computed before taking medians; they need not equal the ratio
of the table's medians. The current custom command spends median0.787s in Cargo,
0.805s build-to-ready and1.237s executing the suite. The selected integration
unit's frontend/export lowering takes0.017s/0.044s, nested within Cargo. Those
scopes must not be added together. Guest execution is the largest current stage
and the next diagnostic target. Cargo's total includes the changed production
library and dependencies, not just the integration unit's exporter receipt.

All32 commands and two unreachable E0308/E0499 controls passed. The eight source
states are original, deliberately wrong prefilter accounting, five cumulative
valid production edits, and compiled restoration. Native and both custom arms
agree on both original per-test outcomes at every state. Cargo check accepts the
wrong semantic edit. Native/check JSON proves fresh production-library and
integration units; every custom command rechecks fre-kernels and reexports the
exact integration target. Custom bytecode/catalog hashes agree between duplicate
arms. Retained executables, bytecode, catalog, selection, call-report, suite,
child-identity and log receipts were independently verified at closure.

The original fre ES8 assertions are unchanged:320,796 exhaustive and24,576
seeded/window comparisons. Both native and custom use two test workers and all
four arms use two Cargo workers and separate new cache namespaces. The adopted
df4006 tool, strict frontend, original pinned fre source and repository profiles
are retained. There is no LLVM/foreign guest backend. Startup, wrong-edit and
restoration costs are retained as controls, excluded from edited timing ratios.

The historical2.678x ES8 result used an old VM, sequential custom tests and18
build workers. It is not a matched before/after speedup comparison. This closed
history establishes the current baseline without attributing the difference to
any one optimization. Next collect bounded current-engine operation and native
sample evidence on these two original tests, then choose a measured runtime
mechanism. Unchanged-build timing is not an optimization target.
