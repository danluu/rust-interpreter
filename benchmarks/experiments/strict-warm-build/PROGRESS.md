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

Stable per-MonoItem code-generation placement remains in qualification.
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

The prepared standard libraries already have identical metadata and source
bytes, but their different physical roots affect imported caller locations.
The reviewed [shared immutable preparation policy](../../../experiments/stable-cgu/SHARED-IMMUTABLE-STD.md)
uses one new physical std key for both modes while retaining separate application
flags and caches. Its [99 source controls](../../../results/shared-std-source-tests-01/README.md)
and actual seven-command shared preparation passed. The new strict36 integration
also passed with the exact same shared key in both mode arms. Source61 is running;
a fresh screen27 still follows. Old keys/results are never relabeled.
Tools04, Tools05 and shared-std01 exhausted their 600-second canonical lock
admissions before starting any compiler work; all are preserved. Tools06 and
shared-std02 ran after the shared slot cleared. The failed cold screen supplies
no warm-build result.

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
now records the actual lowering ID/effect journal and validates the complete
observed context boundary after stock lowering. It remains uncompiled and has
no hit path. The typed body codec and full tree/reference validator are in
progress; structural input counts are not measured reusable-body coverage.
[Native controls](../../../results/hir-body-coverage-native-01/README.md),
[complete development coverage](../../../results/hir-body-development-coverage-01/README.md).

The [external trait-name index](../../../experiments/external-trait-index/README.md)
is a reviewed, uncompiled compiler prototype. It preserves ordinary external
table construction, retains the exact name/namespace projection, and keeps local
mutable tables on the existing path. Prepared controls include an explicit
default-off shadow comparison, internal hygiene/disambiguator/namespace tests,
and native alias/reexport/ambiguity/error histories. Actual hits, memory costs,
compiler qualification and performance remain unmeasured.

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

The unchanged [protocol](PROTOCOL.md) requires all fifteen final Nushell edits
below 0.500 seconds, then frozen fresh-project checks for generalization. These
mechanism screens cannot substitute for those gates.
