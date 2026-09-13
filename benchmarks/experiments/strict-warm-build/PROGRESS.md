# Strict edited-build progress

The 0.500-second target remains unmet. Measurements include the complete
changed-source command through all 14 original Nushell type-relation tests;
the application, test selection and five cumulative production edits are
unchanged. No final latency gate or fresh holdout qualification has passed.

The completed frontend-worker screen found no material improvement: edited
medians were 3.9612s / 3.9807s / 3.9678s for workers1/2/1. The paired median
wall change was -0.12%, within 3.08% observed maximum A/A deviation, with
2.51% more child CPU. All 27 screen commands and 30 separate qualification
commands passed; none of the five candidate edit commands was below 0.5s.
Keep the option off. [Exact history and assessment](../../../results/strict-warm-frontend-worker-screen-01/assessment.md).

The host-library O1 screen also completed with all 27 commands and all original
tests. Edited medians were 4.0088s / 3.9074s / 3.9854s for off/on/off;
paired wall time improved 2.42%, with 2.22% observed maximum A/A deviation
and 0.56% more child CPU. None of the five candidate edits was below 0.5s.
The candidate's one cold observation was 80.63s versus 62.35s / 61.64s for
the controls. Keep the option experimental and off by default; this single
history does not establish a reliable gain or final-target qualification.
[Complete history](../../../results/strict-warm-host-library-screen-01/assessment.md).
Build02 passed 505 Rust tests (two existing ignored), ten Python controls and
all three native/edit/diagnostic histories. The earlier metadata-flag rejection
remains separately [retained](../../../results/host-library-build-failure-01/README.md).

Stable per-MonoItem code-generation placement completed qualification and its
development screen without establishing a performance gain.
All twelve optimized-compiler bootstrap/package stages passed for source
`58e1e1f5311f4424ea81def4763081f6da62d9b3`, including option tracking,
partitioning, native entry and stripping controls.
[Compiler build evidence](../../../results/mono-production-compiler-complete-01/README.md).
The actual installation and matched tool build passed. Workspace02 passed
505 Rust tests (two existing ignored) after a corrected helper path-conversion
failure; all five helper controls passed. Both standard-library preparations
and all 36 strict diagnostic/semantic integration commands passed.
The first source-observable qualification failed at command 38: export
succeeded, but fixture stdout locking called unsupported `pthread_mutexattr_init`
in the VM. The corrected fixture compares all ten fields exactly against retained
native values through integer returns. Its 27 focused controls and all 61 actual
qualification commands passed, including deliberately incorrect expected file
and line values. Raw diagnostics and source validation remain unchanged.
[Fixture controls](../../../results/source-observable-transport-tests-01/README.md).
[Complete actual 61-command history and retained first failure](../../../results/mono-production-source-observables-02/README.md).

The subsequent MonoItem Nushell screen stopped after its three cold commands:
64.1687s / 64.4294s / 63.9284s, each passing all 14 tests. Baseline and duplicate
bytecode were identical; candidate bytecode differed, so the unchanged artifact
parity gate rejected the history before any edited timing. Source restoration
passed. Complete typed inspection identifies 153 trap-message path differences
and 18 constant-data source paths from the two physical standard-library
sysroots; all other typed program fields matched. This comparison does not
qualify the unequal artifacts.
[Failed cold screen and complete typed comparison](../../../results/strict-warm-mono-production-screen-01/README.md).
The runtime trap formatter now uses rustc's runtime/macro remapping scope.
Tools06 and Workspace04 passed (505 Rust tests, four ignored). The explicit
artifact/scope regression passed 67 actual compiler/VM commands. A separate
diagnostic test retained matching native/exported raw JSON but failed its extra
top-level-only filename check on an E0080 nested expansion span. Its corrected
recursive validator passed all 63 actual diagnostic commands in fresh attempt02;
full raw JSON comparisons remain unchanged. Exact compiler/std/binary and source
identity checks bind the separately retained 67-command scope pass to Tools06.
The original diagnostic attempt remains failed.
[Complete scope/diagnostic/tool/workspace evidence](../../../results/trap-span-remapping-controls-01/README.md).

The prepared standard libraries already have identical metadata and source
bytes, but their different physical roots affect imported caller locations.
The reviewed [shared immutable preparation policy](../../../experiments/stable-cgu/SHARED-IMMUTABLE-STD.md)
uses one new physical std key for both modes while retaining separate application
flags and caches. Its [99 source controls](../../../results/shared-std-source-tests-01/README.md)
and actual seven-command shared preparation passed. The new strict36 integration
also passed with the exact same shared key in both mode arms. The new source61
and full screen27 then passed with all original tests, negative controls and
restoration. Old keys/results are never relabeled.
Tools04, Tools05 and shared-std01 exhausted their 600-second canonical lock
admissions before starting any compiler work; all are preserved. Tools06 and
shared-std02 ran after the shared slot cleared. The failed cold screen supplies
no warm-build result.

The fresh MonoItem screen passed exact bytecode/catalog parity across all three
arms and all nine source states. Edited medians were 5.3696s / 5.3454s / 5.0050s
for off/on/off. The median paired wall change was +5.14%, with 6.90% maximum
observed A/A wall deviation; child CPU increased 12.66%. None of the five
candidate edits was below 0.500s. Keep the placement option off: this history
does not establish a gain. The empty-target observations were 62.57s / 64.68s /
64.49s. [All 27 commands and exact qualifications](../../../results/strict-warm-mono-production-screen-02/assessment.md).

A general compiler/std validator change now gathers the same six per-entry
identity fields with one no-follow file stat, plus final directory rechecks.
It still inspects every entry on every invocation. All 33 compiler/std and
inventory-refusal controls passed. Five alternating pairs of the complete
compiler+shared-std loader reduced median wall time from 454.980ms to 167.079ms,
with exact returned values and readiness. This isolates loader cost; Cargo,
tool loading and VM execution are excluded, and no end-to-end saving or latency
qualification is claimed. [Complete first comparison](../../../results/owned-tree-validation-01/README.md).
A follow-up avoids eagerly formatting error paths for successful checks, with
the same predicates, exceptions and messages. All 33 controls passed again;
five new alternating pairs reduced loader median wall time from 157.917ms to
111.974ms, with exact outputs and readiness. This remains a component comparison.
[Complete follow-up comparison](../../../results/owned-tree-validation-02/README.md).

A separate HIR-lowering experiment now has a compiled coverage diagnostic.
Its 54 native fixture commands passed, including exact raw error comparisons,
source shifts and restoration. Four of nine fixture free functions pass the
conservative input gate. A subsequent complete native Nushell check produced
742 reports, including 726 completed compiler invocations and 16 probes, with
zero owner gaps or gate disagreements. Among the 37 incremental invocations,
only 3 of 3,941 free-function records qualified: the same one function in three
`nu-protocol` configurations. The other 689 invocations had incremental disabled.
This coverage is too narrow to justify compiling the current cache for Nushell.
[Full coverage and limits](../../../results/hir-owner-development-coverage-01/README.md).
The earlier whole-owner HIR cache patch remains uncompiled. A separate body-only redesign
preserves ordinary attributes, parameters, signature and generics lowering.
Its diagnostic passed 66 native controls and a complete native Nushell check,
again accounting for all 742 reports with zero owner gaps. The ordinary
`nu-protocol` configurations each admit 482 bodies; the test configuration admits
489. Across 37 incremental invocations, 3,536 of 26,469 body-scope owner records
pass the structural gate. These are invocation-weighted input counts; they do
not establish observed lowering IDs, captured effects, replay, cache hits or
speed. The normal 482 bodies contain 29,817 source bytes and encode 535,975 input
bytes. A reviewed [source-only capture checkpoint](../../../experiments/hir-body-cache/README.md)
now records the actual lowering ID/effect journal and a typed HIR body tree,
validating the complete observed context boundary and tree/reference/allocation
closure after stock lowering. The cold-audit checkpoint also reconstructs HIR privately after stock lowering,
recaptures the complete tree, and rechecks the exit effects; the original stock
HIR remains the result. The cold-audit checkpoint subsequently passed its selected compiler check
and all 22 unit controls, without warnings, failures, skips or filtering.
Its native run-make sequence remains unrun; structural input counts are not measured reusable-body coverage.
The latest capture key also binds active language/library feature declarations
and all eight ordered allow-lists at the actual body-lowering entry. This covers
inputs outside the session-option hash without invoking boolean feature getters.
The qualified cold checkpoint remains capture-only and does not skip ordinary
lowering or feature checks.
An opaque prepared-value converter now validates current IDs, resolutions,
operator/type enums, integer values and source coordinates without constructing
HIR or interning symbols. That converter alone is not a reusable-body admission API.
[Native controls](../../../results/hir-body-coverage-native-01/README.md),
[complete development coverage](../../../results/hir-body-development-coverage-01/README.md).
A separate [limited compiler check driver](../../../experiments/hir-capture-check/README.md)
freezes the earlier journal-only checkpoint `3f3e9c28`; its two configuration
guards and subsequent six configuration/archive controls passed with no skips.
The independent checkout preparation passed after the 24 GiB free-space gate.
The actual selected-crate check then failed with three `E0308` borrowed-key API
errors in the journal's sorting calls; no unit stage ran. Those projections are
corrected in the new full typed/prepared checkpoint, preserving numeric order.
The upgraded prepared-value checkpoint `33f4c4e4` passed all six runner controls
and its exact source application. Its actual compiler check had no remaining
`E0308` but failed the unchanged warnings-as-errors policy: nineteen unreachable
public declarations, one private-interface warning and one unordered feature-set
iteration warning. No unit stage ran. The current successor narrows visibility
and uses stable feature enumeration with independent exact-set validation;
the corrected checkpoint `60d5be45` passed the actual selected-crate compiler
check and all 22 unit controls with zero warnings. Its source is
`9d21c2bae5edcfd6cae6e96f38731a740b7acc9e`, and all 61 plan/application/check/unit
commands are archived with complete source and predecessor proofs. Both failed
histories remain separate and cannot qualify a cache hit.
[Complete cold-audit check and 22-unit evidence](../../../results/hir-cold-audit-check-01/README.md).
[Original failed check and exact source archive](../../../results/hir-capture-check-failed-01/README.md).
[Six upgrade-runner controls](../../../results/hir-upgrade-controls-01/README.md).
[Ten continuation controls](../../../results/hir-cold-audit-upgrade-controls-01/README.md).

The ReadyHit checkpoint implements an exclusive current-context hit token,
complete destination preflight, ordinary ID/binding adapter replay, and HIR
materialization. Reuse is separately selected and default off. Every proposed
hit includes actual journal, recaptured-tree and final-state verification;
there is no fallback after replay starts. The trusted local cache boundary is
explicit: structural checks do not authenticate an intentionally forged,
semantically valid payload with a recomputed checksum. This implementation
passed the actual selected compiler check and all 26 unit controls with zero
warnings, failures, ignored or filtered tests. The truthful compiler source is
`3d7ad8282c5695196f4a4dcfd0bdceacac3f79b9`, parent `9d21c2ba`; all 61 commands,
four supervisors and complete source inventories are archived. The subsequent
native stage1 compiler/std build, three identity probes and tracked-option test
passed. Its run-make failed the first capture assertion before testing hits:
bootstrap sets `RUSTC_FORCE_RUSTC_VERSION=compiletest`, while the cache correctly
disables itself whenever that override is present. No capture or reuse reports
were emitted. The original failed attempt remains preserved; the test setup
needs to exercise the real compiler identity and separately check the override
refusal. Native cache-hit behavior and speed remain unqualified.
The separate existing-compiler probe with the real version identity compiled
the unchanged fixture successfully, but all 24 eligible bodies reported
`rejected-body-tree`. Its full source/compiler guards passed and the produced
native binary was not executed. The fixture environment repair and
phase-specific rejection diagnostics subsequently passed the selected compiler
check and all 26 unit controls, with zero warnings, failures, ignored or filtered
tests. Their actual compiler source is
`0bc623ee4860082df9d1d2216aefad9abb42990d`; all 61 commands and complete source
inventories are archived. The stage1 executable and native standard library
were subsequently rebuilt for this checkpoint; all three compiler identity
probes and the direct fixture compile passed. All 24 records rejected the cold
audit. The produced native binary was not executed and no reuse hit is qualified.
Source review identified an address mismatch: capture stored the WorkerLocal
wrapper address while the audit compared the dereferenced worker arena. The
repair checkpoint `84166943` uses the current worker arena and adds a 27th unit
test rejecting wrapper and foreign-arena identities. All audit checks remain.
Its actual compiler source `7efc0d9484da82cd327deb3b48616f8ec81eaf8d`
passed the selected compiler check and all 27 unit tests, with no warnings,
failures, ignored or filtered tests. All 61 plan/apply/check/unit commands and
the complete source inventories are archived. The stage1 compiler and native
standard library were subsequently rebuilt for this repair. The tracked-option
test and complete native fixture passed, but compiletest truncated the later hit
records, so that original outer attempt remains failed. A separate replay of the
same unmodified recipe preserved the full output and passed all 14 commands,
including final source, restored-fixture and runtime checks. It recorded 335
verified cache hits across 22 names. All tree, journal and poststate audits remain
required. Stage2 packaging, application integration and performance qualification
remain pending.
[Complete native replay and retained original failure](../../../results/hir-arena-native-qualification-01/README.md).
The stage2 packaging controller subsequently passed all eight focused controls
and its metadata plan passed all five source guards, including equality with the
qualified 64-file stage1 runtime. Historical native evidence is read from the
verified archive, preserving it when bootstrap replaces its old output paths.
The plan retains all 27 compiler units, native fixture checks, package checks and
the 24/9/8 GiB capacity thresholds. The stage2 build has not been launched.
[Stage2 controller controls and metadata plan](../../../results/hir-arena-stage2-controls-plan-01/README.md).
[Worker-arena repair check and 27-unit evidence](../../../results/hir-arena-identity-check-01/README.md).
[Complete rebuilt native diagnostic](../../../results/hir-diagnostic-native-01/README.md).
[Fixture and phase-diagnostic check evidence](../../../results/hir-fixture-phase-check-01/README.md).
[Four upgrade-driver controls](../../../results/hir-fixture-phase-upgrade-controls-01/README.md).
[Direct capture diagnostic and unchanged compiler evidence](../../../results/hir-direct-capture-probe-01/README.md).
[ReadyHit compiler check and 26-unit evidence](../../../results/hir-ready-hit-check-01/README.md).
[Failed native attempt and unchanged compiler evidence](../../../results/hir-native-correctness-failed-01/README.md).
[Fourteen upgrade-driver controls and retained initial launcher failure](../../../results/hir-ready-hit-upgrade-python-controls-01/README.md).
The [native correctness driver](../../../experiments/hir-native-correctness/README.md)
requires this exact successful history before building stage1 rustc/std, testing
the tracked option, and running the native recipe with visible hit diagnostics.
Its six Python boundary controls passed. This is a correctness sequence, not a
performance qualification.
[Six native-driver controls and archive attempts](../../../results/hir-native-correctness-controls-01/README.md).
The parser successor also passed all seven controls, including the actual
emitted `S`/`E` suffix and exclusive `ItemLocalId` bounds.
[Seven corrected hit-parser controls](../../../results/hir-native-parser-controls-01/README.md).
[Configuration guard evidence](../../../results/hir-capture-configuration-guards-01/README.md).
[Copied archive guard evidence](../../../results/hir-capture-offline-seed-guards-01/README.md).

The ordinary native baseline for interpreted Cargo build scripts passed all 28
planned outcomes: 19 successful three-test runs, eight uncalled compilation
rejections and one deliberate wrong-value test rejection. All fixture sources
were restored. The histories cover generated files, Cargo directives, input and
environment changes, unchanged-run freshness, and a helper also used by a native
proc macro. Both earlier recorder failures and the admission timeout remain
preserved. This establishes the native comparison; interpreted host-unit routing
and complete build-script execution still need implementation.
[Native build-script baseline](../../../results/interpreted-build-scripts-native-baseline-01/README.md).

The opt-in Darwin descriptor operations (open, write, close and descriptor flags)
are implemented and passed native comparison checks in both interpreter engines.
After integration with main, the release workspace suite passed 533 tests with
10 ignored tests and no failures or filtering; both native controls and all
17 child commands passed. This supplies file-descriptor primitives; complete
standard-library file/stream support and interpreted Cargo host-unit routing
remain pending. No build-time improvement is claimed from these checks.
[Integrated descriptor correctness evidence](../../../results/descriptor-io-integrated-qualification-01/README.md).

Three strict lowering audits of the unchanged native-qualified build script
reported the same first blocker: `libc::unix::getcwd`. The four compiler commands
passed; no build script or guest program executed.
[Original export support census](../../../results/build-script-export-census-02/README.md).
The subsequent opt-in Darwin `getcwd` implementation passed 540 release
workspace tests (10 ignored, none failed or filtered), both native comparison
tests and all 33 child commands. It supports native NULL allocation semantics,
checked guest buffers, shared allocation budgets and errno preservation. The
getcwd implementation then advanced the unchanged build-script export census
to `fstat` in the default/shared-helper configurations and `_exit` in the
subprocess configuration. No guest or native build script executed.
[Getcwd correctness evidence](../../../results/getcwd-native-qualification-01/README.md).
[Subsequent export census](../../../results/build-script-export-census-03/README.md).

The subsequent default-disabled Darwin fstat primitive passed 551 release
workspace tests (10 ignored), all 15 required controls and 49 native comparison
commands. Its complete result bytes, SDK layout, errno and descriptor ownership
checks passed in both engines. The archive preserves the earlier SDK-selection
and compiler-API failures. Full build-script execution and a latency improvement
remain unestablished.
[Fstat qualification](../../../results/fstat-native-qualification-03/README.md).

The unchanged build-script export census subsequently advanced to
`pthread_mutex_lock` in the default/shared-helper configurations; the subprocess
configuration still stops at `_exit`. All four compiler commands passed, with
no build-script or guest execution. Supporting the printing path requires the
mutex initialization, ownership and destruction lifecycle as well as lock and
unlock operations.
[Post-fstat export census](../../../results/build-script-export-census-04/README.md).

Explicit build/runtime compiler-role binding is implemented with the default
route preserved. Its integration with getcwd passed 548 release workspace
tests (10 ignored, none failed or filtered), all twelve required controls,
and both native getcwd tests with 33 child commands. Default exporter
capabilities and the wrapper's null role probe passed. Building an exporter
against the modified frontend still needs actual private metadata/linker and
loaded-driver qualification. No latency improvement is established.
[Merged default qualification](../../../results/exporter-roles-getcwd-qualification-01/README.md).

The composed private build sysroot subsequently passed the stock compiler
smoke test: 18 correctness controls and ten source guards, with actual cache
hits, matching raw uncalled type errors and restored source. The genuine beta
compiler built unchanged stock rustc main, whose executable loaded the qualified
modified driver and LLVM. All earlier inspection, metadata, compiler build and archive
failures remain preserved. This qualifies that composition and stock executable;
the exporter build and application latency checks remain pending.
[Stock compiler compatibility evidence](../../../results/embedded-frontend-stock-smoke-01/README.md).

The [external trait-name index](../../../experiments/external-trait-index/README.md)
is a reviewed, uncompiled compiler prototype. It preserves ordinary external
table construction, retains the exact name/namespace projection, and keeps local
mutable tables on the existing path. Prepared controls include an explicit
default-off shadow comparison, internal hygiene/disambiguator/namespace tests,
and native alias/reexport/ambiguity/error histories. Actual hits, memory costs,
compiler qualification and performance remain unmeasured.
The unchanged production compiler passed all 33 commands in the ordinary
fixture baseline, covering 18 source states and restoration. The index was not
enabled, so this verifies fixture behavior only.
[Ordinary fixture evidence](../../../results/external-trait-index-ordinary-fixtures-01/README.md).

The proposed proc-macro span-handle table passed four standalone container
controls against the exact patched source. A separate source-only bridge
integration fixture now covers real transport and compiler-server boundaries,
with explicit side effects, stale handles and same/cross-thread controls. Its
four Python expectation tests passed against the unchanged fixture and span
patch. The installed stock-store compiler subsequently built the real bridge
test executable, and all four native tests passed together, serially and without
filtering. This qualifies the fixture against the stock store; the patched
store and compiler-server histories remain unrun, and no gain is established.
[Control evidence](../../../results/proc-macro-span-handle-controls-01/README.md).
[Four expectation tests](../../../results/span-bridge-expectations-tests-01/README.md).
[Actual stock-store native bridge baseline](../../../results/span-bridge-native-baseline-01/README.md).

Three generated Cargo target directories from the completed worker screen
were retired. Original bytecode, source, cache metadata, publication inputs and
all results were preserved and checked again. The operation reclaimed an
observed 8.16 GiB without controlling another process.
[Retirement evidence](../../../results/worker-screen-target-retirement-01/README.md).
The three completed host-library screen targets were also retired after retaining
and checking their required artifacts, bindings and publication proofs, reclaiming
an observed 8.16 GiB. All original screen evidence remains available.
[Host target retirement](../../../results/host-library-screen-target-retirement-01/README.md).
The three failed first MonoItem screen targets were subsequently retired after
retaining and rechecking their source, artifacts and compiler dependency proofs.
The observed recovery was 6.57 GiB; original failed-screen evidence remains
available. [Exact retirement evidence](../../../results/mono-failed-screen-target-retirement-01/README.md).
The completed second MonoItem screen's three targets were subsequently retired,
recovering an observed 8.36 GiB. All 27 commands, 14 tests per source state,
artifact parity and the negative performance assessment remain preserved.
[Completed screen retirement](../../../results/mono-screen02-target-retirement-01/README.md).

The unchanged [protocol](PROTOCOL.md) requires all fifteen final Nushell edits
below 0.500 seconds, then frozen fresh-project checks for generalization. These
mechanism screens cannot substitute for those gates.
