The composed candidate passes the pgrust guard, with no meaningful latency
change: median paired wall ratio 1.00177 (+0.18%) and CPU ratio 1.00973 (+0.97%).
All 132 complete commands pass their expected outcomes, including three wrong
production edits, all original assertions and compiling/executing restored
source. Fifteen valid edited pairs and fifteen same-session A/A pairs were
retained. The descriptive A/A envelopes are 2.38% wall and 1.56% CPU, within the
predeclared 4%/3% limits; they are not confidence intervals.

Median complete edited commands were 0.550s candidate, 0.546s retained custom,
0.549s duplicate custom, 0.596s ordinary Cargo/libtest and 0.607s the explicit
line-tables native control. Median paired candidate/native wall ratio is 0.94157.
Pgrust already uses line-tables-only debugging, so the second native row does
not establish a debugging-setting improvement. All modes used two Cargo workers;
custom suites used two prepared workers, with fresh guest state per test, and
native controls used libtest's default concurrency. The four original tests
and repository profile were unchanged.

The repository disables incremental compilation. `--function-cache auto`
therefore performed full lowering, with an explicit off report, on every
candidate command. The initial forced-reuse attempt stopped before any edited
pair and is preserved separately; none of its timings enters this result.
The new automatic-mode tool is 9abacd0a72846d7721771b4a48c63f6178eb15f272698dd243404a395e3b6f2b.

This is the small-target guard for the composition. It does not establish the
required compute-heavy gain or qualify an automatic default. Continue the
already planned token/folded comparisons and the original-selection anchor.
