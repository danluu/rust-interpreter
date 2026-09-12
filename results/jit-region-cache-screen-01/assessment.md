# Park the larger local cache

The candidate passes 339 Rust tests in debug and release (one ignored), including
64 deterministic generated programs exercised across instruction limits, cache
pressure, full-width aliases, native calls, loops and interpreted fallbacks.
The existing cache regressions also run in both ordinary and resumable modes.
Eight real-suite commands preserve all 34 passing test outcomes and four pgrust
wrong-edit outcomes, with exact entropy replay, logical counts and guest peaks.

The fixed six-pair token screen improves paired wall time by **0.11%** and CPU
by **0.08%**, far short of the predeclared 10% wall gate. Individual wall changes
span −1.00% to +0.22%; this is effectively a tie. The generated arena shrinks
from 14,643,348 to 14,616,736 bytes while logical instructions, native calls and
the 322 persistent register pairs remain unchanged. There are no JIT declines.

Park `experiment/jit-region-cache-20260912`; do not merge its runtime, retime it
or start the conditional edit/held-out promotion runs. This screen includes VM
startup and JIT preparation, excludes compilation, and is conditional on two
recorded entropy streams for the older three-test token artifact. It does not
measure the expanded twelve-test suite or predict whole-command improvement.

The control is `40cca8a7` (main's diagnostic-era VM); candidate `d16f2bba` was
built from `d1e1b69`. The first real-suite controller attempt stopped before any
VM child because a relative entropy-library path was not resolved for the
provenance manifest. The corrected controller passes; Rust sources were unchanged.

Next add artifact-bound selection for per-test profiling, then measure the
expanded suite's dominant tests on the retained VM. Assess region formation,
native transition frequency and redundant work before choosing another emitter
candidate. Increasing either persistent assignment capacity or local cache
capacity has now failed to identify a useful next optimization.

[Measurements](summary.json) · [Build](../jit-region-cache-build-01/summary.json) ·
[Real-suite correctness](../jit-region-cache-smoke-02/summary.json) ·
[Plan](../../benchmarks/experiments/jit-region-cache/PLAN.md)
