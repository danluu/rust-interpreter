# Scalar native Call primary: parked

All 40 complete changed-source commands preserve the 12 original assertions,
wrong-result failures, bytecode identity and source restoration. The candidate
misses the unchanged prospective gate: paired wall ratio **1.003720** (+0.37%),
CPU **0.996103** (-0.39%), maximum A/A wall deviation **3.0585%** and CPU
**1.2237%**. The wall ratio plus A/A deviation is **1.034305**. This is a
failed engineering gate, not proof of zero effect. No retries, full comparisons,
held-out commands or parser comparisons followed. The unfinished full scaffold
was removed without execution. Runtime adoption remains unchanged.

Candidate tool `7a967d16de13e446a87e9695a1e553476b92592fbfcba60ace9329e0d404b6e8`
contains the custom native scalar Call bridge; only it enables
`--jit-scalar-calls`. Matched control/duplicate use `4a1381c4…`; both sides
retain the same strict compiler/exporter, automatic function cache, two Cargo
workers and two prepared suite workers. Timing uses ordinary OS entropy.
No unchanged build contributes to edited-pair ratios. Candidate/native paired
wall is 1.587458 in this run; this selected suite does not qualify an entire
project. Setup was 122.34s for this tool's five qualification/build commands.

The closure verifies 1,571 frozen inputs, 56 retained artifact snapshots and
1,669 evidence files, including the terminal receipts. The build passed 590
workspace tests per profile (10 ignored), strict/cache qualification passed
121 commands, and six diagnostic original-test executions preserve per-PC
logical counts, memory, entropy and exact code-map reconstruction. Failed
intermediate qualification attempts remain recorded separately. Correctness
qualification does not establish performance.

Paired observations from these same five edits: VM execution median delta
-36.27ms (ratio0.985857); Cargo +12.01ms; build-to-ready +13.31ms. The long
block-boundary test's median delta is -40.06ms. These are descriptive, nested
and overlapping observations, not additive causal effects or extra gates.
The unchanged compiler and matching artifacts do not justify attributing the
Cargo delta to a new exporter mechanism.

Next investigate scalar code quality: the first body emitter spills every
computed SSA value and reloads uses, with no register allocation. Any revision
needs its own proof, differential tests, exact profiles and prospective
changed-source screen. The existing bridge guards and private-failure replay
remain mandatory. Do not retime the unchanged candidate.
