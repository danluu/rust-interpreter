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
The actual HIR cache patch remains uncompiled. A separate body-only redesign
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
closure after stock lowering. It remains uncompiled and has no materializer or
hit path. Twenty prepared unit controls and the native run-make sequence remain
unrun; structural input counts are not measured reusable-body coverage.
The latest capture key also binds active language/library feature declarations
and all eight ordered allow-lists at the actual body-lowering entry. This covers
inputs outside the session-option hash without invoking boolean feature getters.
It remains capture-only and does not skip ordinary lowering or feature checks.
An opaque prepared-value converter now validates current IDs, resolutions,
operator/type enums, integer values and source coordinates without constructing
HIR or interning symbols. It is still not a reusable-body admission API.
[Native controls](../../../results/hir-body-coverage-native-01/README.md),
[complete development coverage](../../../results/hir-body-development-coverage-01/README.md).
A separate [limited compiler check driver](../../../experiments/hir-capture-check/README.md)
freezes the earlier journal-only checkpoint `3f3e9c28`; its two configuration
guards and subsequent six configuration/archive controls passed with no skips.
The independent checkout preparation passed after the 24 GiB free-space gate.
The actual selected-crate check then failed with three `E0308` borrowed-key API
errors in the journal's sorting calls; no unit stage ran. Those projections are
corrected in the new full typed/prepared checkpoint, preserving numeric order.
Its new check and all twenty unit controls remain pending. The original failed
journal-only check cannot qualify the newer codec or a cache hit.
[Configuration guard evidence](../../../results/hir-capture-configuration-guards-01/README.md).
[Copied archive guard evidence](../../../results/hir-capture-offline-seed-guards-01/README.md).

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
controls against the exact patched source. This does not qualify bridge
integration or establish a performance gain.
[Control evidence](../../../results/proc-macro-span-handle-controls-01/README.md).

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
