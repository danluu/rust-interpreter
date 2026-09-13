# Guarded indirect-call edited-command comparison

The candidate retains the qualified f8713aaa wide-operation runtime, exporter
and wrapper, adding one guarded indirect target per observed call site. Baseline
and its A/A duplicate use f8713aaa; the fixed full-suite anchor is fe9dcae0.
All tool bytes are checked against build and execution proofs and frozen in the
run manifest. Lookup caching remains off on every route.

Candidate tool: `9e219e2ecb7cc05b2946f30467b9f3d0886e676355d50dcabf94740a82864c2c`.
VM: `fe7f39996e41ffeb1eb5b7393d085d551037f60947b7ff78500910e5be68dad1`.
The host build passes both required profiles; runtime and driver checks follow.

Require 424 debug and release tests, 123 Python checks, seven exact original
selections, nine serial/prepared suite commands, 203 strict native/cache checks
and three current profile replays before timing. Profile replays compare every
logical PC count against the completed wide-operation run. Publication counts,
native indirect hits and remaining VM calls establish actual use. Remaining VM
calls include first use, different targets and other declines; they do not
identify a unique reason. These instrumented runs establish no speedup.

The full twelve-test token suite is primary, including both dominant tests.
Folded and pgrust are mandatory even if token misses its performance gate.
Every case has three cycles, five valid cumulative edits, original and wrong
states in each cycle, then compiled restoration: 154 commands, fifteen edited
pairs and fifteen A/A pairs. Original test sources and expected failures stay
unchanged. Candidate, baseline and duplicate must export identical artifacts.

Four custom orders are 0,1,3,2; 1,2,0,3; 2,3,1,0; 3,0,2,1, where 0 is baseline,
1 duplicate, 2 candidate and 3 anchor. Each four-state block balances positions
and adjacent pairs; fifteen edits leave an incomplete last block. Native
repository and line-tables controls alternate around the custom group. Cargo
check runs last. Each route has a fresh, separate cache. Two Cargo workers and
two prepared custom workers remain fixed; native retains default libtest
concurrency. Every route receives each changed source state.

For each wall/CPU A/A envelope, take the largest absolute per-edit median
duplicate/baseline deviation across three cycles. These are descriptive
engineering margins, not confidence intervals. The prospective primary gate
requires component wall gain greater than the wall envelope, at least 8% wall
gain over the fixed anchor, and CPU ratios at most 1 versus both controls.
Additionally, maximum CPU ratio plus CPU envelope must be at most 1.05.
Held-outs require maximum ratio versus baseline/anchor plus the corresponding
A/A envelope to be at most 1.05, independently for wall and CPU. There is no
separate absolute noise ceiling. This requires more headroom for noisy
near-regressions while allowing large measured gains. Historical decisions
remain governed by their original rules.

The driver freezes code, plans, proof files, source pins, test selection and
installed bytes before commands. Require the shared lock within 45 seconds,
12 GiB free for fre or 8 GiB for pgrust, and 8 GiB before each child. Stop and
preserve any unexpected outcome, provenance, lock or storage failure. No
automatic retries, partial-pair replacement, outlier omission or retiming an
unchanged candidate to seek acceptance. Report complete commands, nested
stages and descriptive worker durations separately.
