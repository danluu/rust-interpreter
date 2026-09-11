# Cold compilation has broader concurrency than edited compilation

Read-only inspection reproduces all nine saved Cargo timing parses and checks
their original HTML hashes. No compiler or guest command was started. These
are the older instrumented b2/78 interface measurements, not additional samples
for the lightweight-wrapper experiment.

| Cold mode | Cargo jobs | Timed Cargo units | Child CPU / wall | Maximum reported overlap | Span with at least four reported intervals |
| --- | ---: | ---: | ---: | ---: | ---: |
| Native | 18 | 608 | 7.079 | 19 | 66.5% |
| b2 baseline | 4 | 800 | 3.115 | 5 | 86.6% |
| 78 candidate | 4 | 800 | 3.164 | 5 | 87.9% |

For the API edit, all modes have nineteen timed units. The custom CPU/wall
quotients fall to 1.547 and 1.478, and only 7.0%/6.2% of the reported spans have
four overlapping intervals. Native's edited quotient is 3.054. Cold and edited
commands therefore present different scheduling opportunities.

The overlap histogram integrates the reported decimal intervals and verifies
both total span and the sum of unit durations. It describes Cargo's rounded
intervals, not running CPU cores or work waiting in a scheduler queue. Reported
overlap can exceed the configured job count. The 192 additional custom units
also do not prove redundant work: host/target/profile/feature distinctions must
remain intact. Package counts are preserved in the [summary](summary.json).

Inference: a separate comparison of custom worker counts is now worth testing
before attempting broader dependency-cache sharing. The custom cold commands
have substantial interval overlap under four jobs, whereas the edited commands
have much less. These observations do not predict a speedup or establish an
optimal worker count. Finish the fixed wrapper comparison first; preserve its
four-job custom controls and original gates. Any subsequent worker experiment
must use identical binaries, original tests/source controls and separate cache
histories, with cold and warm behavior measured independently.

Supervisor 83228 completed with status 0. Source and snapshot hashes, the full
histograms and all nine rows are recorded in the summary. Constant/relocation
identity remains an independent prerequisite for function-artifact reuse.
