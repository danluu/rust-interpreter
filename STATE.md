# Current state — September 11, 2026

The unbounded goal remains active: improve the custom Rust development engine
using real source-edit/build/test benchmarks. Every item in `suggestions.txt`
has an [explicit decision](docs/SUGGESTIONS-REVIEW-20260911.md); that user-owned
file remains unchanged and untracked. Local commits are authorized; no push.
Branch: `experiment/resumable-native-calls`.

## Current state

The retained build is `5b2330c/9637b0ac`; [STATUS.md](STATUS.md) contains its
compute, held-out, cold and Cargo-check measurements. The normal source and
installed tool remain unchanged by the failed scalar experiment.

Scalar value calls are implemented end to end in our interpreter, custom
AArch64 emitter and strict MIR exporter. Source is ordinary `crates/` code on
branch `experiment/scalar-value-abi`, worktree `.work/scalar-value-source`.
Measured source commit `840fdb5` exactly matches qualified source `aa56492e`.
The timing composition `ba4ad407` uses that compiler/runtime and the retained
wrapper; Cargo publication was independently qualified.

The [short real-edit screen](results/scalar-edit-smoke-01/assessment.md) is
complete: token paired wall −0.74%, CPU −2.66%; folded wall −0.41%, CPU +1.07%.
It fails the predeclared 8% token screen. All original assertions and wrong-edit
controls passed, with 42 primary commands, 14 independent Cargo checks and
28 executed artifact snapshots. **The candidate is parked.** No full scalar
A/A or held-out histories will run for this candidate.

Token execution saved 170ms at the median paired difference while Cargo added
144ms. Focus next on retained-exporter cost attribution and tuned native
controls, then unfiltered suite execution. Tool lookup is about 2ms, std-MIR
lookup 36–38ms and artifact hashing about 10ms in this screen.

The source branch also contains release native-readiness checks, clearer unsafe
and terminal-fault contracts, custom engine default members, automatic Python
and formatting checks, a dedicated formatting commit and shared 18-worker
latency defaults. These changes are separate from the measured source.
The first maintenance check caught a missing sparse-worktree corpus fixture;
that fixture was restored. The [completed maintenance check](results/review-maintenance-01/assessment.md)
passes all 334 release Rust tests (one ignored), 11 Python tests and formatting.
No Rust test started in the failed first attempt.

The completed budget cache batch is closed: sixteen exact completed caches were
archived and decoded/verified, with all 245 external proof hashes unchanged.
Sources, executed snapshots, logs and installed tools remain. No additional
archive is planned before the next engine experiment. New detailed inventories
stay local under [the retention policy](results/RETENTION.md).

## Persistent rules

- No subagents or independent models. Custom guest interpreter/emitter only.
- Strict type/borrow checks and original assertions; no fake unwinding/threads.
- Serialize task builds, tests, profiles and benchmarks with `.work/benchmark.lock`.
- Never signal or control unrelated work. Never queue lock users behind a live archive batch.
- Local commits authorized; no push. No new AWS purchase/activation.
- Private rg-aot output is aggregate-only. `suggestions.txt` remains user-owned and untracked.
- Source and executed evidence are preserved; old gates are not rewritten after results.

[Next work](RUNTIME-NEXT.md) · [Current review](docs/SUGGESTIONS-REVIEW-20260911.md).
