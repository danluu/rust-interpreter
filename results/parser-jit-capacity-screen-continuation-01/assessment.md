# Larger code capacity did not pass the parser screen

The explicit 32 MiB treatment is parked. Its median paired improvement over
explicit 16 MiB is 0.69% in complete changed-source wall time, inside the 4.04%
observed 16/16 variation. The declared wall gate fails. No full three-cycle
study will run for this unchanged treatment, and the default remains 16 MiB.

| Five valid production edits | Median paired ratio | Observed A/A envelope | Ratio plus envelope | Gate |
| --- | ---: | ---: | ---: | --- |
| 32 MiB / 16 MiB wall | 0.993115 | 0.040447 | 1.033563 | Fail: must be < 1 |
| 32 MiB / 16 MiB child-tree CPU | 0.994581 | 0.035381 | 1.029963 | Pass: must be <= 1.03 |

The CPU pass is narrow and does not override the wall failure. These envelopes
are empirical same-session variation, not confidence intervals. Against the
ordinary native control, the 32 MiB treatment takes 1.1981 times the wall time
and 1.2420 times the CPU. Each ratio is the median of five paired edited-state
ratios, not a ratio of independent time medians.

The complete 32-command protocol ran every original gram_core test after the
original state, a wrong initial-lookahead constructor, five cumulative valid
production edits, and restoration. All 114 outcomes agree across native and
all three custom arms. The wrong edit produces eight passes and 106 assertion
failures in every arm. Assertions were unchanged, the source restored, and
4,965 frozen inputs verified. Within each source state all custom artifact and
catalog bytes agree. Cold and restored artifacts are not forcibly normalized.

All arms used CARGO_INCREMENTAL=1 and two Cargo workers. Native used default
libtest threading; custom used two prepared workers. Guest instruction and
allocation bounds remained 100 billion and 150,000 per test, with 64 MiB guest
memory. Generated code was bounded separately at 16 or 32 MiB per owner; these
bounds do not measure host peak RSS. Both custom capacities used the same
immutable VM/exporter/wrapper and paid the explicit capability probe. Initial
admission required 24 GiB free and every command rechecked the 8 GiB floor.

The first attempt stopped after five controls because failed-test receipts omit
runtime counters. No valid edited timing preceded that harness failure. An
offline audit retained those five commands; the continuation executed exactly
the remaining 27. The original failure is preserved in
[its report](../parser-jit-capacity-screen-01-failure/summary.json). New validator
tests require successful-test statistics and keep unavailable failed-test
counters explicitly unavailable. The schedule and thresholds stayed fixed.

Independent stage medians give context: custom16 A spent 1.124 s in Cargo and
0.382 s executing; custom32 spent 1.086 s and 0.375 s respectively. The dominant
C-vector test's median was 0.226 s at 16 MiB A and 0.210 s at 32 MiB. Its median
interpreted operations fell from 4,830,685 to 301,209. These nested timers and
independently aggregated medians cannot be summed or subtracted to explain the
paired command ratio, and the observed Cargo difference is not caused by JIT
capacity merely because it appears in this run.

The [offline analysis](../parser-jit-capacity-screen-analysis-01/summary.json)
revalidates all commands and preserved artifacts. An earlier exact profile
shows the large routine reaches 93,652 of 140,615 bytecode positions (66.60%),
so a mostly-unused-function explanation is not supported. The typed
[initialization check](../parser-function-initialization-01/summary.json) shows
its 102,786 registers already avoid bulk initial zeroing. Its frame is 372,497
bytes; actual frame-clearing cost has not been measured. Reached-region JIT
work remains conditional on better evidence rather than this failed capacity
screen. The next runtime investigation returns to composition of guarded memory
facts and local-value forwarding in the measured token bottleneck.

Exact results and identities are in [summary.json](summary.json). The prototype
and replay harness are retained on branch `experiment/jit-capacity-20260913`;
no capacity performance change is adopted by this report.
