# Current state — September 12, 2026

The unbounded goal remains active: improve the custom Rust development engine
using real source-edit/build/test benchmarks. Every item in `suggestions.txt`
has an [explicit decision](docs/SUGGESTIONS-REVIEW-20260912.md); that user-owned
file remains unchanged and untracked. Local commits, private GitHub publication and regular pushes of qualified changes to main are authorized.
Repository: `danluu/rust-interpreter` (private); qualified work goes to `main`.

## Current state

The corrected composed tool `8b16be8e` passes393 Rust tests per profile,93 Python checks, seven exact saved tests, nine suite commands and203 native/cache commands. Its full twelve-test token comparison passes all132 correctness/control commands but does not pass adoption: observed paired wall improvement4.91% misses8%, and the3.67% A/A CPU envelope exceeds3%. Observed CPU usage falls8.61%; candidate wall remains2.140× ordinary native libtest and2.362× the line-tables control. Keep all fifteen pairs and do not retime this implementation to seek a pass. Folded, pgrust and the original three-test anchor are continuing. VM execution dominates at3.938s versus0.734s lowering (0.183s rebinding), so the next changed implementation targets call state and frame transfers. The original build03 remains held for its invalid padding proof; the corrected build uses the preserved alignment invariant. [Token decision and stages](results/composed-development-edit-token-03/stage-assessment.md), [alignment audit](results/composed-frame-alignment-review-01/assessment.md).

Explicit parallel isolated suites pass365Rust tests/profile and56Python tests.
The five-edit token complete-command screen improves wall time34.3% with3.2%
more CPU. All40 commands, original assertions, wrong edits and restoration
checks pass. Candidate5.330s versus retained custom8.021s; the candidate still
takes2.216× the paired two-process native control. Fresh guest state and one
creating-thread JIT owner per worker are preserved. One worker remains default;
folded/pgrust complete-command guards also pass (−2.1%/+3.2% wall). The earlier saved-runtime screen
was41.8% faster and excluded checking/export.
[Edit decision](results/parallel-suites-edit-token-01/assessment.md).

The replacement September12 suggestions change the next optimization priority:
qualify and measure a composed build with modest correct components against a
fixed anchor, rather than requiring every component to win8–10% independently.
Use fresh A/A controls, original edits, stronger ordinary Cargo/libtest native
controls and held-outs. Old failed gates remain failed; no multiplied-ratio
prediction is treated as evidence. Call-protocol and exporter-binding work
follow the composition's measured costs. Safe metadata cleanup enabled the
current benchmark; it is maintenance, not optimizer progress.

Seeded valid-program differential coverage passes all362workspace tests in both
profiles plus768additional seeds/profile. Programs cover loops, diamonds,
calls, widths, heap/linear aliases, budgets, code declines and exact PC counts.
The final VM build stopped on storage after both test profiles passed; runtime
sources are unchanged, so this tests-only feature needs no new VM publication.
The parallel worker follow-up is recorded above.
[Coverage](results/generated-cfg-campaign-01/assessment.md).

Split heap/linear native address checks are parked. All363host tests/profile
and42saved-suite commands pass, but token regresses2.51% wall/2.50% CPU across
six pairs and two recorded entropy streams. No real-edit promotion follows.
The emitter remains off main. The seeded differential follow-up is complete
above; the next workflow direction is independent test concurrency.
[Decision](results/native-address-checks-screen-01/assessment.md).

Exact saved-test selection now works independently of instruction profiling.
The feature passes 360 host tests per profile and seven real selections with
identical instructions, output, memory peaks and replayed entropy. Six native
sampling windows show different hot paths in the two dominant token tests:
regex determinization/hashing versus sorting, comparison and precondition
checks. Generated code accounts for about 89% of both captures; bytecode-count
reductions alone remain a poor guide. The subsequent arena-branch experiment
is recorded above and stays parked.
[Selection and native samples](results/selected-native-block-sample-01/assessment.md).

Shared-call specialization is parked on
`experiment/constant-call-specialization-20260912`. The final version passes386
host tests/profile and all34saved real assertions, but its three-pair runtime
medians are +1.57% token, −0.46% folded and −0.45% pgrust. CFG cleanup and proven
unobserved frame-write removal reduce bytecode operations without useful native
runtime gains. The compiler remains off main and no edited-command screen ran.
The separate named-test selection and native sampling follow-up is complete
above; this compiler candidate remains parked.
[Decision](results/constant-specialize-replay-03/assessment.md).

Catalog-bound single-test profiling passes 340 Rust tests/profile and fourteen
real VM commands. Seven current token/folded/pgrust test profiles exactly match
fresh retained-VM controls under replayed entropy. Their saved bytecode stays
unchanged. The expanded token test emphasizes regex determinization; the original
exhaustive test emphasizes bounds and copy preconditions. The subsequent private
pointer promotion and shared-call candidates are parked; current native samples
now guide further work. [Profiles](results/suite-profiling-real-01/assessment.md).

The larger region-local cache is parked off main after 339 Rust tests/profile
and exact real-suite correctness passed but its six-pair token runtime screen
improved only 0.11% wall and 0.08% CPU, missing the fixed 10% gate. No retiming or
conditional edit promotion follows. Next enable exact per-test profiles for the
expanded suite and choose a structural direction from its dominant tests.
[Decision](results/jit-region-cache-screen-01/assessment.md).

The register-width feasibility diagnostic passes 337 Rust tests/profile and
rejects the packing candidate before emission: only 7,628 additional token
native reads out of 10.45 billion, and 900 out of 3.44 billion folded reads, on
exact historical profiled artifacts. Current restored suite artifacts also pass
the static census. Generated assignments remain unchanged. Next test a larger
local cache using otherwise idle native registers, with a fixed 10% saved-runtime
screen before real-edit promotion. [Decision](results/jit-register-width-weighted-01/assessment.md).

The optional prepared JIT and isolated Cargo runner are published on main.
All 320 Rust tests per profile (one ignored), 36 initial Python tests and 96 real
source-edit/check/restoration commands pass. Across five distinct edits each,
prepared/fresh wall ratios are 1.0084 for pgrust, 0.9686 for token and 0.8916 for
folded. These are descriptive single-cycle results. The larger batch saves
repeated preparation; token remains dominated by guest execution.
[Pgrust](results/prepared-suite-pgrust-01/assessment.md),
[token](results/prepared-suite-token-01/assessment.md),
[folded](results/prepared-suite-folded-01/assessment.md).

The Nushell saved-artifact pilot passes four separate native tests plus five VM
commands. The artifact-bound catalog fix passes 322 Rust tests per profile,
40 Python tests, a 16-command real Rust fixture, Ruff's actual export (12
commands), and pgrust's full edit sequence (32 commands). Catalogs preserve
explicit function IDs despite optimization and bind them to exact bytecode.

Fre's corrected actual export passes eight commands, including three native
assertions and exact fresh/prepared replay. The first controller omitted the
reference's 150,000 allocation limit and used the default 100,000; this caused
the recorded allocation trap. Recompilation at the correct limit produces the
same bytecode and passes. The older/newer failing controls used that same wrong
limit, so they did not establish a lowering defect. The correction is explicit
and the failed evidence remains preserved. The catalog fix is published on main. Effective runtime limits now also pass
323 Rust tests/profile, 41 Python tests, twelve controlled saved-suite commands
and 32 actual pgrust edit/check/restoration commands. Checked test discovery now
also passes 325 Rust tests/profile, 44 Python tests, 25 fixture commands and six
real-project listing controls. All four pgrust hashfn and 389 fre-kernels names
match native libtest, including seven ignored tests. Those names now feed the
filtered runner qualified below. Full
ignore/should-panic/unwind/thread execution semantics remain open.
[Discovery qualification](results/test-discovery-qualification-01/assessment.md).

Automatic filtered suites are now qualified by 329 Rust tests/profile, 48 Python
tests, 44 fixture commands and 96 actual edit/build/test/check commands. Filtering
uses the same checked compiler invocation as export. Single tests work; ignored
tests are skipped; expected-panic, empty and oversized selections fail before
execution. Across pgrust/folded/twelve-test token, edited automatic medians are
0.533/1.726/8.267 s, versus native 0.673/1.711/3.059 s. All 24 paired source states
produce identical automatic/explicit bytecode and match native test outcomes.
These are one-cycle descriptive results. Token expands the old three-test
subset; its first attempt stopped on disk admission before any valid edit, and
the successful retry used fresh caches with more headroom. Next measure the
feasibility of narrower persistent native-register assignments.
[Filtered suite qualification](results/filtered-suites-qualification-01/assessment.md).
[Ruff repair](results/prepared-catalog-ruff-01/summary.json),
[pgrust catalogs](results/prepared-catalog-pgrust-02/assessment.md),
[fre corrected qualification](results/prepared-catalog-token-corrected-02/summary.json),
[original misconfigured run](results/prepared-catalog-token-01/summary.json).

Cross-region rematerialization remains parked after its 0.78% wall/0.81% CPU
runtime regression. No conditional promotion benchmarks will run.
[Decision](results/jit-remat-screen-01/assessment.md).

Persistent function reuse is correct but its first complete-command screen
misses the fixed 8% gate: 5.30% paired edited wall improvement and 4.32% CPU.
All 21 primary commands, 7 independent checks and 14 bytecode comparisons pass.
The candidate stays opt-in and disabled by default; its conditional promotion
holdouts are canceled. Do not retime it. Guest execution remains about 3.1 s
of the 4.7 s command, versus native's 2.2 s complete command. The current-source JIT is now measured against the historical VM: effectively
tied (0.18% median difference across six controlled runtime pairs). Fresh
samples put 88.64% in generated code; the subsequent rematerialization screen
failed as recorded above.
[Decision](results/export-reuse-screen-token-01/assessment.md).

Earlier runtime qualification: integer helper inlining improves Ruff 5.8%, pgrust 3.0% and five additional workloads 2.8–7.5% relative to the scalar-inlining VM, with unchanged semantics and passing regression guards. All 297 debug/release tests and 588 comparison commands pass (one Rust test ignored). [Integer-inlining assessment](results/binary-inline-20260912/assessment.md). These gains primarily concern interpretation. The new JIT diagnosis is in [its assessment](results/jit-merged-token-01/assessment.md); the unbounded whole-command optimization goal remains active.

Inlining the complete checked scalar-memory path is now qualified: pgrust improves 6.7% and four Fre cases improve 2.1–5.0% relative to the frame-loop VM `f33b40d`. Other public cases stay within regression guards in both engines. All 297 workspace tests pass in debug and release (one ignored); all 588 comparison commands preserve outputs, instructions and peak guest memory. Only three inline attributes change; method bodies and checks remain intact. [Scalar-inlining assessment](results/complete-scalar-inline-20260912/assessment.md). These are saved-bytecode runtime measurements; full edit/build/test latency and unknown holdouts remain unmeasured.

Fixed frame clearing is **parked** on `experiment/fixed-frame-clear`. The
[fresh combined es8 confirmation](results/fixed-frame-clear-combined-confirm-01/summary.json)
improves complete edit/build/test commands by 7.39% wall and 7.61% CPU across
15 pairs, missing the predeclared 8% wall gate. All 96 commands, 48 artifacts
and wrong-edit/restoration controls pass. The earlier isolated-source 8.37%
confirmation and eight successful library regression gates remain historical
evidence; they do not override the failed combined gate. Remaining comparisons
are canceled and the runtime change stays off main. Broad combined correctness
passes 300 debug/release tests (one ignored), 47,004 native differential
commands, 245 TLS checks, 382 fre bodies (seven ignored), and 52 integration
assertions. [Decision](results/fixed-frame-clear-combined-01/assessment.md).

Exporter reuse now has a qualified cost observer (41 debug/release tests and
104 original-fixture commands). The real token/folded histories each execute
five edits, a wrong edit, an original anchor and a restored-source rebuild.
Exactly repeated function outputs cover median 178ms/460ms on token and
44ms/96ms on folded. Token restoration initially stopped on an incorrect
cold-anchor expectation; its output exactly matches the retained exporter’s
existing restored-state history, without a rerun. The source is restored.
[Token census](results/export-reuse-token-01/assessment.md),
[folded census](results/export-reuse-folded-01/assessment.md).

Typed relocation observation is now qualified: 44 debug/release exporter tests
and 179 original-fixture commands pass, including exclusion of eleven actual
compiler TypeId allocations. The typed token/folded histories preserve all eight
artifacts and expected assertion outcomes. Using prior unannotated weights,
repeated templates cover median 454ms (99.02%) on token and 90ms (87.61%) on
folded. [Token](results/export-reuse-token-02/assessment.md),
[folded](results/export-reuse-folded-02/assessment.md). Every binding reconstructs
the original bytes; no executable output is rewritten or reused.

Compiler dependency observation now passes 229 small semantic-edit commands,
179 complex-fixture commands and eight states each on token and folded. Every
function was fully lowered; no green node changed its typed template. Green
functions cover median 444ms/81ms of earlier work, with 22ms/16ms spent checking
green status (excluding key construction). [Token](results/export-reuse-token-03/assessment.md),
[folded](results/export-reuse-folded-04/assessment.md). Next implement binding
recipes and actual reuse. The payload must retain frame-packing observations,
replay graph interactions in order and preserve current allocation aliases.
This is not yet a measured end-to-end saving.

Current-MIR binding recipes now pass 47 exporter tests per profile, 231 complex
fixture commands, 229 semantic-edit commands, and all eight states on token and
folded. Encoded/decoded payloads reconstruct 5,203 token functions (172 declines)
and 1,041 folded functions (four declines) in a second graph. Exact output,
frame observations, scheduling, guest memory and alias classes match. The
payloads are 61 MB/15 MB in the initial representation. [Token](results/export-reuse-token-04/assessment.md),
[folded](results/export-reuse-folded-05/assessment.md). Next verify payloads from
prior compiler sessions, using rustc's incremental directory transaction;
original lowering still always executes today.
The two-stream entropy diagnostic establishes exact token execution across both
VMs and engines with identical inputs; it makes no performance claim.

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
