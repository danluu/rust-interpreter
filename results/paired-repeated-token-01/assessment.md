# Repeated token edits: controls verified, cache-history difference found

Three cycles completed 63 commands: 45 edited commands, 9 wrong-edit controls,
3 initial cold commands and 6 original-source anchors. Every warm command
followed a real source change for that mode. Original fre tests were unchanged,
the pinned source was restored, all wrong edits failed, and all valid edits
passed. Six measurement-helper tests include CPU accounting through a real child
and grandchild. [Control verification](verification.json).

| Complete edited command | Median wall time | Median child CPU |
| --- | ---: | ---: |
| Native repository test profile, four jobs, one test thread | 2.085 s | 2.056 s |
| Previous custom JIT `6bf10fda` | 7.205 s | 7.170 s |
| Retained custom JIT `57a54edd` | 6.974 s | 6.941 s |

The retained engine was faster in all fifteen pairs against its previous build;
the median paired difference was −267 ms wall and −282 ms CPU. It remained
substantially slower than the specified native control. This run validates the
new measurement protocol and repeats a scoped runtime comparison; it does not
choose a tuned native configuration or qualify broad project use.

The initial qualification also required all 42 artifacts to match the earlier
single-cycle run. **That check failed.** Eighteen match and twenty-four differ.
All baseline/candidate pairs match at each state; cycles two and three also match
each other. The first six states change after revisiting source, while the final
edit is byte-identical in every cycle. The original failure is retained in
[initial-qualification-failure.log](initial-qualification-failure.log).

A typed comparison of the two original-source artifacts finds the same 5,421
function headers and operation counts, with 8,524 immediate-value changes in
1,619 functions. Readonly data grows by 192 bytes; mutable-static contents also
change. No other opcode fields change in that comparison. This is consistent
with changed constant allocation/relocation layout, but **is not an equivalence
proof or an established root cause**. We did not normalize addresses, discard
samples, or silently waive the failed check. Cross-history determinism remains
an exporter/cache investigation. [Structural diagnostic](artifact-history-diagnostic.json).

The benchmark's source, command, CPU, mode-order, wrong-edit and within-pair
artifact checks pass independently of that stronger cross-history assertion.
Use the per-cycle artifacts and histories when reproducing this result.
[Raw summary and all edited pairs](summary.json), [timing report](summary.md).

Tools, downloaded dependencies and std-MIR setup were prepared before these
commands. “Cold” means empty per-run Cargo targets, not a cold OS cache or a
fresh tool installation. No other host work was stopped or reprioritized.
