# Current state — September 12, 2026

The unbounded goal remains active: improve the custom Rust development engine
using real source-edit/build/test benchmarks. Every item in `suggestions.txt`
has an [explicit decision](docs/SUGGESTIONS-REVIEW-20260911.md); that user-owned
file remains unchanged and untracked. Local commits, private GitHub publication and regular pushes of qualified changes to main are authorized.
Repository: `danluu/rust-interpreter` (private); qualified work goes to `main`.

## Current state

The user's current priority is build-time improvement. The in-flight runtime work is finished: integer helper inlining improves Ruff 5.8%, pgrust 3.0% and five additional workloads 2.8–7.5% relative to the scalar-inlining VM, with unchanged semantics and passing regression guards. All 297 debug/release tests and 588 comparison commands pass (one Rust test ignored). [Integer-inlining assessment](results/binary-inline-20260912/assessment.md). Next work measures compiler/export/cache build latency separately from execution; the unbounded optimization goal remains active.

Inlining the complete checked scalar-memory path is now qualified: pgrust improves 6.7% and four Fre cases improve 2.1–5.0% relative to the frame-loop VM `f33b40d`. Other public cases stay within regression guards in both engines. All 297 workspace tests pass in debug and release (one ignored); all 588 comparison commands preserve outputs, instructions and peak guest memory. Only three inline attributes change; method bodies and checks remain intact. [Scalar-inlining assessment](results/complete-scalar-inline-20260912/assessment.md). These are saved-bytecode runtime measurements; full edit/build/test latency and unknown holdouts remain unmeasured.

Fixed frame clearing is implemented on `experiment/fixed-frame-clear`, with
runtime source `6f9e148` and candidate tool `fdbf713b`. It preserves all frame
zeroing and specializes statically known extents up to 256 bytes. The
[three-history es8 confirmation](results/fixed-frame-clear-confirm-02/assessment.md)
passes the predeclared aggregate gate: 8.37% complete-command wall improvement,
8.48% CPU, 15 real edited pairs; the initial pilot is excluded. Each history
and all wrong-edit/restoration controls remain available. Candidate commands
remain roughly 2.5 times native on this target.

Broad qualification passes 47,004 native differential commands, 245 TLS checks,
382 fre bodies with seven ignored, and all 52 integration assertions. The
baseline and candidate share the exact exporter and wrapper. Nine original
library workflow gates remain before runtime retention; keep this candidate
separate from the historical full-workflow anchor below. Good tooling and
evidence changes can be published independently of the experimental runtime.

Keeping interpreter frame state across ordinary instructions is now qualified: an additional 26.8% saved-artifact runtime gain on pgrust and 28.1% on Ruff relative to the qualified arithmetic/scalar-memory VM. Five additional workloads improve 15.2–29.4%, with JIT within wall/CPU regression guards. All 297 workspace tests pass in debug and release (one ignored); all 588 comparison commands preserve results, instructions and peak guest memory. [Frame-loop assessment](results/same-frame-interpreter-20260912/assessment.md). Bounds checks remain; complete edit/build/test latency and unknown holdouts were not measured.

General interpreter arithmetic and scalar-memory improvements are now qualified
in source: about 12.7% faster saved-artifact execution on pgrust/Ruff and
14.6–20.5% on four additional Fre cases. All 297 workspace tests pass in debug
and release (one ignored); 308 final comparison commands preserve outputs,
instruction counts and peak memory, with JIT inside its regression guards.
The [runtime assessment](results/general-interpreter-20260912/assessment.md)
retains the fixed gates and two earlier failed screens. It measures runtime
including VM startup; complete edit/build/test latency was not measured.
The immutable tool and full-workflow anchor below remain historical references.

The retained build is `5b2330c/9637b0ac`; [STATUS.md](STATUS.md) contains its
compute, held-out, cold and Cargo-check measurements. The compiler/runtime and installed tool remain unchanged by the failed scalar experiment. The launcher now supports explicit integration targets.

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
144ms. Retained-exporter attribution is now complete. Native profiles, fre calibration and unfiltered coverage have since been measured. Next use integration edits, remaining native controls and lowering reuse to choose substantial work. Tool lookup is about 2ms, std-MIR
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

Native-tuned-calibration-01 is complete and inconclusive: line tables improved
calibration command wall by 7.86%, missing the fixed 8% screen; no debuginfo
improved 5.17%. No preset was selected before the last two edits. All 21 Cargo
commands, 15 diagnostic repeats, wrong-edit controls and source restoration
passed; ten parser/selection tests pass. Cargo-reported build durations barely
changed, while suite execution decreased. Repeats use the workspace cwd and
lack Cargo's full injected test environment; they remain separate diagnostics.
No guest change; a large native-control target remains open.
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

## Unfiltered suite and integration targets

`cargo test -p fre-kernels` ran without filters: 382 unit tests and 52 integration
tests passed; seven unit tests were ignored. Two doc tests passed and one failed
because the pinned nightly omitted expected diagnostic E0451. The controller
stopped on original source before either edit, restored source and is terminal.
See [the baseline failure](results/fre-unfiltered-native-01/assessment.md). Its
9.615s duration is failure latency, not a successful edit-to-suite result.
The existing 389-name custom replay exactly covers the native library target,
excluding ten integration executables and all three doc tests.

The normal launcher now exposes `--test-body --test-target NAME`, integrated
from qualified source `759bbbc`. Integration targets share dependency metadata
while exact Cargo target matching selects their separate sidecars. Four unit
checks and 14 Cargo/native/custom fixture commands cover A/B/A switching,
wrong edits, strict uncalled errors and the unchanged library route.

[All 52 original fre integration assertions pass](results/fre-integration-targets-02/assessment.md)
across ten targets. A first driver attempt prefixed entry names incorrectly;
its failed exports remain recorded. Native test names work unchanged.

The [five-edit integration pilot](results/fre-integration-edit-01/assessment.md)
passes: median custom 0.816s, native 1.015s, check 0.539s; paired wall −20.4%
and CPU −41.1%. All modes use 18 jobs and warm primed caches. All 21 commands,
42 logs and seven snapshots are preserved. Original assertions reject the wrong
edit, and every measured edit recompiles. The compute-heavy es8i target now provides that contrast: custom 3.867s versus
native 1.449s and check 0.529s, paired wall 2.678× and CPU 1.860×. All 24
commands and eight snapshots verify, including original-source rebuilds after
restoration. This workload fails the pilot target and will not be retried to
change that outcome. Native runs its two tests with default threads; custom
bodies are sequential. See fre-integration-es8-edit-01.

Three owned es8i profiles pass and bind all sampled PCs to their own code dumps.
98.33% of 7,662 samples are generated execution, 14.81% clearing and 14.66%
cursor loads/stores; host boundaries are 0.80%. Next measure a stronger frame
initialization proof before changing runtime behavior. Original assertions,
alias semantics, alignment padding and exact faults/limits stay intact.

The root integration probe exposed a harness bug: restoring staged source kept
an old modification time and Cargo reused the final edit's artifact. The helper
now refreshes mtime before restoration. An actual native Cargo regression fails
before and passes after; all 18 root Python tests pass. The fresh root fre probe
rebuilds and passes original assertions. Its bytecode still differs from an
earlier original-source artifact, so export determinism remains open.

Task processes are terminal. Current fre native/check/shared custom targets are
available for the next comparison. Two completed alternative native-profile
caches and two older completed fre native caches were retired after exact
ownership, terminal, open-file and preserved-evidence checks; their final test
executables and logs remain. No archives were created. Check current free space
against the 8GiB floor before starting further builds. Additional completed
scalar host incremental caches and old fre/stopped-Ruff incremental metadata
were retired locally; all protected artifacts/logs remain. Another session uses
the shared lock periodically; wait without controlling its processes.

## Persistent rules

- No subagents or independent models. Custom guest interpreter/emitter only.
- Strict type/borrow checks and original assertions; no fake unwinding/threads.
- Serialize task builds, tests, profiles and benchmarks with `.work/benchmark.lock`.
- Never signal or control unrelated work. Never queue lock users behind a live archive batch.
- Merge qualified changes to main and push regularly to the private GitHub repo. No new AWS purchase/activation.
- Private rg-aot output is aggregate-only. `suggestions.txt` remains user-owned and untracked.
- Source and executed evidence are preserved; old gates are not rewritten after results.

[Next work](RUNTIME-NEXT.md) · [Current review](docs/SUGGESTIONS-REVIEW-20260911.md).
