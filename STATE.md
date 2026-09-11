# Continuation checkpoint — September 10, 2026

The goal remains active: improve the custom Rust development engine using real
source-edit/build/test measurements. The user asked for every suggestion in
`suggestions.txt` to be considered and appropriate fixes applied. The complete
[review decisions](docs/SUGGESTIONS-REVIEW-20260910.md) and implemented follow-ups
are checked in. The user's `suggestions.txt` remains unmodified and untracked.

Current source includes the JIT limit/safety fix (`a2a0e04`, tool `b2aa6efe`).
It passes 188 bytecode, 11 exporter and 3 historical cache tests. The last full
performance-qualified engine is `57a54edd`; its historical results remain
separate from newer source changes. [Exact Git/build index](benchmarks/tool-builds.json).

The repeated token run completed 63 commands. Within-pair artifacts match, but
the same source produced different data/immediate layout after the first edit
cycle. The stronger cross-history check failed and is preserved, not normalized
away. Two native-control qualifications completed another 168 commands, including
42 independent checks; nine measurement/control helper tests pass.

The durable full-corpus experiment is **`native-controls-corpus-01`**, launched
from committed harness `e3d748f`. Authoritative live state:

- `.work/experiments/native-controls-corpus-01/status.json` — supervisor receipt.
- `.work/corpus-runs/native-controls-corpus-01/status.json` — case progress.
- `.work/corpus-runs/native-controls-corpus-01/plan.json` — exact options and frozen scripts.
- `.work/continuation-state.json` — detailed current checkpoint and source pins.

At launch the supervisor/controller were PIDs **34318/34324**. They initially
waited for the benchmark lock before pgrust. Re-check receipts and actual process
identities before treating a run as live. A separate user-owned disk-cleanup task
has been using the same lock; do not interrupt or modify it. The coordinator
waits up to ten minutes per lock acquisition and preserves failures.

The corpus uses three actual-edit cycles per workflow, O0/incremental native
compilation with 18 jobs/default test concurrency, four custom build jobs, and a
separate Cargo-check reference. This is a specified native candidate, not a claim
to have found the fastest configuration. Report frontend/link and compute rows
separately. Preserve every negative edit, source restoration and artifact check.

After the corpus, investigate constant/relocation identity across cache histories
and a larger native-call transition. Use typed eligibility and preserve call
frames, argument/results, exact budgets, traps and TLS cleanup. The latest CPU
and frame diagnostics are linked in [the evidence index](results/INDEX.md).

No subagents, external model calls, AWS activation, unrelated process control,
broad cache deletion, private cleanup or quarantine deletion. Keep measured
scripts frozen and serialize this task's builds/tests/benchmarks/cleanup under
`.work/benchmark.lock`. Local commits are authorized; no remote was requested.
Old checkpoints and results remain historical evidence rather than live state.
