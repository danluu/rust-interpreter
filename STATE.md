# Current state — September 12, 2026

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
144ms. Retained-exporter attribution is now complete. Focus next on effective native
profiles and tuned controls, then lowering reuse and unfiltered suite execution. Tool lookup is about 2ms, std-MIR
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

## Export-cost result

The optional timing observer is source `7b5062a` on `experiment/export-costs`,
worktree `.work/export-costs-source`, composed tool `a338a98d`. It uses the exact
retained VM and wrapper. [Qualification and real edits](results/export-costs-token-02/assessment.md)
pass 39 exporter tests, 18 VM/native fixture comparisons, strict uncalled error
controls, and seven byte-identical real artifacts with restored fre source.

Median exclusive outer costs: graph lowering 691ms, artifact hash 49ms,
publication 30ms, serialization 14ms, validation 5ms. Nested graph costs:
reachable MIR/local passes 464ms, aggregate finalization 97ms, call optimization
61ms, CFG 54ms. Aggregate capture adds 96ms inside the 464ms interval. Do not
sum nested scopes. Small publication/hash changes cannot justify another full
primary; investigate graph reuse and stronger native controls.

Cargo's effective-profile inspection passed 15 metadata queries across fre,
pgrust, Nushell, Ruff and private rg-aot, with no builds/tests. Pgrust/Ruff use
line tables already; the others use full debuginfo; all use unpacked split info.
Debug=0 also activates Cargo's automatic debuginfo stripping, now recorded.
The first inspection guard rejected that known profile change; the second
records it explicitly and verifies all other profile fields remain equal.

The original 135 edited native commands now have suite timing: token 0.61s,
folded 0.30s, and near-zero native execution on most frontend workflows. Outside
suite time is a residual, not pure compilation. Nushell type-relations has a
grouped harness; the rest use libtest. See native-existing-stages-01.

Next experiment: native-tuned-calibration, three native debug presets on the
seven existing fre token source states. Edits 1–3 select the preset; edits 4–5
confirm it. Actual Cargo commands remain primary; native binary repeats are
separate diagnostics. Ten parser/selection tests pass. No guest change.
Completed scalar-smoke native/check caches and four custom incremental folders
were deleted after exact ownership/terminal/open-file and 48 preserved-hash
checks. Freed about 1.78GB; no archive. Local detail is under
`.work/native-control-cache-retirement-01`; all executed bytecode remains.

The first observer build stopped on an incorrect expected test count; all 39
Rust tests had passed. The first profile passed transparency checks but stopped
on space admission before real edits. One exact completed 103.5MB logical host
cache was deleted after ownership/open-file/preservation checks. Installed tools,
source and test logs remain; no new archive was created. All task processes are
terminal. The maintenance build target is now disposable/retired, so future
host compilation will recreate it.

## Persistent rules

- No subagents or independent models. Custom guest interpreter/emitter only.
- Strict type/borrow checks and original assertions; no fake unwinding/threads.
- Serialize task builds, tests, profiles and benchmarks with `.work/benchmark.lock`.
- Never signal or control unrelated work. Never queue lock users behind a live archive batch.
- Local commits authorized; no push. No new AWS purchase/activation.
- Private rg-aot output is aggregate-only. `suggestions.txt` remains user-owned and untracked.
- Source and executed evidence are preserved; old gates are not rewritten after results.

[Next work](RUNTIME-NEXT.md) · [Current review](docs/SUGGESTIONS-REVIEW-20260911.md).
