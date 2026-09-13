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
The separate source-observable qualification failed at command 38: export
succeeded, but fixture stdout locking called unsupported `pthread_mutexattr_init`
in the VM. Its completed source/diagnostic checks and failure are retained;
full source-observable qualification and the Nushell screen remain pending.
The proposed fixture adapter will compare each observable byte and coordinate
against independently retained native values through supported integer returns.
It must pass fresh controls before any performance screen.

A separate HIR-lowering experiment now has a compiled coverage diagnostic.
Its 54 native fixture commands passed, including exact raw error comparisons,
source shifts and restoration. Four of nine fixture free functions pass the
conservative input gate. This is not application coverage or a cache-hit result;
the HIR cache compiler patch itself remains uncompiled and unmeasured.

Only three generated Cargo target directories from the completed worker screen
were retired. Original bytecode, source, cache metadata, publication inputs and
all results were preserved and checked again. The operation reclaimed an
observed 8.16 GiB without controlling another process.
[Retirement evidence](../../../results/worker-screen-target-retirement-01/README.md).

The unchanged [protocol](PROTOCOL.md) requires all fifteen final Nushell edits
below 0.500 seconds, then frozen fresh-project checks for generalization. These
mechanism screens cannot substitute for those gates.
