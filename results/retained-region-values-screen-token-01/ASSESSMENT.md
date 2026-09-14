# Retained region values did not pass the primary

All 40 commands preserve the 12 original assertions, deliberate wrong-edit
failures, five valid edits, candidate/control bytecode identity and restoration.
The performance gate fails: paired wall ratio 0.994524 (0.55% improvement),
CPU ratio 1.010389 (1.04% increase), and maximum absolute A/A wall deviation
0.026185. The wall margin is 1.020709; CPU also misses the required <=1 ratio.

Park the immutable candidate `76345e9c49cf908287c4dd395db9f59fb06b2c987d83ea26647d989b52ed1dbd`.
No full histories or parser guards start. Adopted runtime `df4006e0` remains the
control. This result does not prove zero benefit in every workload, but does not
justify adoption or another unchanged screen.

Descriptive paired execution is 24.44 ms slower; block/exhaustive test medians
increase 19.44 / 11.99 ms. Cargo is 53.82 ms lower despite byte-identical compiler
binaries. Nested stages and overlapping test times are not additive or causal.
The earlier profiles' additional preparation work and smaller emitted bodies
therefore do not establish a net gain. Reassess preparation's share using closed
real-suite counters before choosing the next implementation.

Closure verifies 1,670 evidence files and 56 artifacts. Minimum recorded free
space is 14,832,631,808 bytes. See [summary.json](summary.json),
[stage-observations.json](stage-observations.json) and [closure.json](closure.json).
