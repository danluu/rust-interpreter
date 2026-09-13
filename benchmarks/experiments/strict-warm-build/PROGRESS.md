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

Two candidates remain in qualification:

- Conservative O1 compilation of native host libraries. Application profiles,
  effective checks, build-script settings, guest compilation and proc-macro
  crate compilation remain fixed. All 84 publication/screen/assessment
  compatibility tests passed. Build01 passed 504 Rust tests and two of three
  native histories; the third rejected Cargo's ordinary metadata-embedding
  flag. The corrected parser preserves that flag, with a new regression test.
  Fresh build02 qualification and the off/on/off Nushell screen are pending.
  [Source checks](../../../results/host-library-screen-source-tests-01/README.md).
- Stable per-MonoItem code-generation placement using an optimized compiler
  build. All twelve bootstrap/package stages passed for compiler source
  `58e1e1f5311f4424ea81def4763081f6da62d9b3`, including option tracking,
  partitioning, native entry and stripping controls. Installation and the first
  matched interpreter-tool build passed. The workspace helper failed before
  any tests because it passed a JSON string to a path-based hashing API; that
  helper is corrected. Updated tools/workspace tests, both standard-library preparations,
  strict diagnostics/source-observable qualification and the Nushell screen
  are separate remaining gates.
  [Required post-build sequence](../../../experiments/stable-cgu/POST-DRIVER-QUALIFICATION.md).

A separate source experiment investigates reuse of unchanged HIR lowering.
Its initial conservative subset is a feasibility step, with no compiled or
measured performance claim.

Only three generated Cargo target directories from the completed worker screen
were retired. Original bytecode, source, cache metadata, publication inputs and
all results were preserved and checked again. The operation reclaimed an
observed 8.16 GiB without controlling another process.
[Retirement evidence](../../../results/worker-screen-target-retirement-01/README.md).

The unchanged [protocol](PROTOCOL.md) requires all fifteen final Nushell edits
below 0.500 seconds, then frozen fresh-project checks for generalization. These
mechanism screens cannot substitute for those gates.
