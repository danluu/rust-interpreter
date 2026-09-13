# Complete parser edits under the repository profile

The custom engine is slower for this complete parser workload under pgrust's
default nonincremental profile. Across 15 changed-source pairs, median paired
custom/native wall and child-tree CPU ratios are 1.157776 and 1.082915.

| Quantity | Native | Custom A |
| --- | ---: | ---: |
| Median complete edited build/test wall | 2.791313 s | 3.224697 s |
| Median child-tree CPU | 3.074548 s | 3.334723 s |

These are independent command medians; the paired ratios above are not ratios
of these medians. The identical custom B/A comparison has median wall ratio
0.988783 and CPU ratio 0.990445. Maximum absolute per-edit median deviations
across three cycles are 2.4634% wall and 2.4259% CPU. These describe observed
variation, not confidence intervals or native-control uncertainty.

All 114 original gram_core tests run at every state, including the C reference
vectors. Each of three cycles has original, wrong initial-lookahead and five
cumulative production edits; the final original is also built and executed.
The wrong edits produce the same native/custom assertion outcomes. The five
valid states produce five distinct bytecode artifacts, each identical across
custom arms and repeated cycles. All source/assertions restore and 4,926 frozen
inputs verify. Both engines use two Cargo workers; native libtest keeps its
default thread count and custom execution uses two isolated prepared workers.

The first controller stopped after two successful original commands because it
required Cargo's `Checking` label; the pinned test profile printed `Compiling`
while still invoking cargo check and the exporter. The independent prefix audit
verified both commands before the validator repair. This continuation preserves
those two observations, verifies their exact commands/cache histories and runs
64 unstarted commands, totaling 66. No completed command is repeated. Originals,
wrong controls and restoration are excluded from the 15 edited pairs.

Custom-A median Cargo time is 2.768108s, its pre-execution boundary is 2.799858s,
and guest execution is 0.394900s. Exporter frontend and lowering medians are
1.685021s and 0.638180s. These timers have different/nested scopes and must not
be summed as a disjoint decomposition. The compiler reports that automatic
function reuse is disabled by the project's incremental setting: all 11,816
required bodies are lowered each time. Most complete-command time is upstream
of guest execution.

The separate matched incremental experiment is retained as a stopped 22-command
prefix, without a performance verdict: restoring original source changes the
readonly constant layout despite all 114 tests passing. Diagnose that history
before changing the engine or declaring an incremental comparison successful.
The supported parser selection does not establish whole-database coverage.
