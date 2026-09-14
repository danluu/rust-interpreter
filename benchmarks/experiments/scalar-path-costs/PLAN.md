# Compare successful machine paths in two parked scalar backends

The direct path emitter passed correctness but failed its changed-source primary:
wall 0.984509, CPU 1.001640, wall A/A 0.025402. Execution differs by +4.62 ms.
Before another implementation, inspect its actual machine instruction work
against the earlier parked store-log backend on the same three original profiles.
Neither backend is adopted. The adopted scalar-only bodies provide byte-identity
controls, not a whole-command performance comparison.

Read only the closed machine code, operation maps and profiles. Decode our scalar
entry's direct branches, conditional branches and fixed status returns, rejecting
all other control instructions, external edges, unproved return statuses and
cycles. Compute min/max word counts over CFG paths that return success. Treat
conditions independently; infeasible combinations widen these bounds. Separate
SP-relative integer loads/stores, other-base integer loads/stores, control and
other words. SP accesses include arguments and profiling output as well as spills.
Distinguish words that can still reach ordinary replay in this conservative CFG;
this is a graph property, not a semantic guard/commit attribution.

Report per-body bounds and successful-call-weighted bounds for exactly matched
functions and scalar hit vectors. Preserve unmatched sets and declines explicitly.
Never add separately minimized categories as one feasible path. The saved code is
profiled. These bounds exclude failed attempts, ordinary callers/fallbacks, JIT
preparation and hardware speculation; they are not retired instructions, causal
attribution or a latency prediction. No guest runs, JIT publication or Rust build.

Require independent enumerated-path controls and strict retained evidence hashes.
Reuse closed exact code reconstruction through its hashes; freshly validate the
complete code partition, matching profile/operation identity and original outcomes.
Shared lock, 12 GiB initial admission and 8 GiB floor.
Freeze inputs, retain every diagnostic and close before choosing a new candidate.
