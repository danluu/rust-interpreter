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

The subsequent MonoItem Nushell screen stopped after its three cold commands:
64.1687s / 64.4294s / 63.9284s, each passing all 14 tests. Baseline and duplicate
bytecode were identical; candidate bytecode differed, so the unchanged artifact
parity gate rejected the history before any edited timing. Source restoration
passed. Initial inspection identifies embedded standard-library source paths
from the two prepared sysroots. The exporter uses diagnostic span formatting
inside runtime trap messages, contrary to rustc's artifact API contract. A
runtime-remapping correction and full structured mismatch diagnosis are underway;
the failed history is retained and supplies no warm-build result.

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
preserves ordinary attributes, parameters, signature and generics lowering;
its diagnostic gate remains in development.

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
