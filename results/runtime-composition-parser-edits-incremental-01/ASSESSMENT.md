# Correct parser history fails the declared CPU guard

All 88 commands completed normally. All 114 original tests, wrong-edit
outcomes, source restoration, frozen inputs and paired candidate/control
bytecode/catalog identities match. The 15 valid edited pairs use normal
entropy, two Cargo/prepared workers and matched incremental compilation.
Original, wrong and restored states are not latency pairs.

| Metric | Candidate / adopted | A/A envelope | Ratio plus envelope | Limit |
| --- | ---: | ---: | ---: | ---: |
| Wall |0.9964519186|0.0483500737|1.0448019922|1.05|
| Child-tree CPU |1.0054002208|0.0448177645|1.0502179853|1.05|

The wall guard passes and the CPU guard narrowly fails. Observed wall time
improves 0.355%, while CPU increases 0.540%; neither establishes a speedup
beyond control variation. Candidate/native ratios are 1.3473088064 wall and
1.3060255081 CPU. The candidate remains slower than native for this parser.

Keep the original threshold. Do not rerun unchanged measurements to seek a
pass or replace control variation with a retrospective rule. Cancel the
unstarted repository-profile history and park the composition. The five
passing project guards remain valid evidence, but do not override this failed
parser guard or admit runtime adoption. Main keeps its adopted runtime.
