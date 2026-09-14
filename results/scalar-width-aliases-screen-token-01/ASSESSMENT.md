The width-alias candidate is parked. All 40 commands preserve original assertions,
deliberate wrong-result failure, restoration and candidate/control bytecode
identity. Median edited-pair wall ratio is 1.028289 and CPU ratio 0.987340.
Maximum A/A deviations are 0.040899 wall and 0.021283 CPU; the wall margin is
1.069188 and fails the unchanged primary gate. No later comparison was started.

Qualification passes 22 focused native/Call controls and 600 workspace tests in
each profile (13 ignored), 121 strict Cargo/cache commands, six exact original
profiles, and 13 screen / 3 observation / 419 launcher controls (22 skipped).
Relative to the preceding dead-register candidate, scalar native bytes shrink
16,712 to 15,544 (block), 14,984 to 13,800 (exhaustive) and 1,304 to 1,184 (folded).
These smaller bodies and 117 million modeled alias computations do not establish
an end-to-end gain. Exact original-PC counts, peak memory, entropy and complete
native code reconstruction pass.

Descriptive median Cargo, build-to-ready and execution deltas are +54.2 ms,
+55.9 ms and +29.7 ms. They overlap, are not additive, and do not establish causal
attribution. Candidate/native median paired wall ratio is 1.57261 for this
selected workflow. Do not compare separate screens as a causal A/B experiment.

Next inspect generated input and stack loads on these saved bodies. Removing
cast nodes may remove useful cached values and expose repeated input loads;
that is a hypothesis to quantify, not a conclusion from the wall timings. Keep
this candidate and all failed gates; no rerun or threshold relaxation.
