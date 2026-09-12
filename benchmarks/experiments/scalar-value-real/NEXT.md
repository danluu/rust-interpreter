Compiler/runtime candidate is frozen and qualified:
- Tool aa56492e192ef2e87f69ed417b34c8f717b28c31a0fa67f5d63fbb92f313c9cd,
  installed .work/interpreter-tools/<key>.
- Compiler source .work/scalar-value-compiler-build-02/tool-source, recipe
  scalar-value-compiler-v2. 334 debug/release tests, one ignored.
- Direct frontend: scalar-value-frontend-02, 424 commands/360 VM comparisons.
- Cargo: scalar-value-cargo-01, 19 commands, original assertions, strict cold
  errors, flag/header/audit/trace checks. The qualified external launcher is
  benchmarks/experiments/scalar-value-cargo/launcher.py, not root interpreter.py.
- Real smoke: scalar-value-real-01, four commands, both original batches on
  V5 and V6. No proof/JIT declines, no performance measurement.

Next stage the existing scripts/bench_e2e_workflow.py into a new scalar workflow
recipe. Preserve every existing assert/measurement/source-restoration/control;
do not edit the frozen root harness or launcher. Add candidate scalar selection
to config, recorded tool settings, command, launcher receipt and artifact-header
checks. Use the qualified new launcher on both baseline/candidate sides so its
fixed overhead is shared. A/A uses exact production key 9637b0ac on both sides,
with scalar disabled; candidate uses aa56492e with scalar enabled. Root harness
already imports ROOT from interpreter through PYTHONPATH, so a staged copy can
live under its run directory. Freeze both harness and launcher paths/hashes.

The existing whole-call-inline/workflows.py and verify_workflow.py demonstrate
the retained three-cycle/five-edit protocol and changed-compiler verifier.
Preserve its controls, allowing only the exact new tool identities and explicit
scalar setting. Independently verify each command's scalar flag, launch setting,
artifact header/hash, source states and all original assertions. Qualify staging
and rejection controls before starting timings. Do not change the root files or
frozen old recipe files.

Run fresh interleaved histories in original fixed order: A/A folded, A/A token,
candidate folded, candidate token. Each case has 63 primary commands, 21 separate
Cargo checks, 15 edited pairs and 42 snapshots. Token requires >=10% complete-
command wall improvement beyond A/A, with improving CPU; folded keeps separate
5% wall/CPU guards. Then seven held-outs if primary passes. Native profile/jobs/
compiler flags and original case/source hashes stay matched. Instruction counts
or one smoke invocation cannot decide retention.

Space: about 9.5 GiB remained after real smoke; preserve the 8 GiB command floor.
Smoke allocated only small fresh custom caches, but full histories also retain
native/check caches and 42 artifacts each. Do not blindly copy the old 4 GiB
workflow allowance or lower it to fit. Measure exact completed comparable target
footprints and artifact sizes; preserve completed parked caches with the existing
qualified archive lifecycle as needed. Prior Call-slot workflow caches were
archived; budget-register workflow caches remain. The provenance adapter is
benchmarks/experiments/published-build-cache/runtime.py, currently Call-slot-only;
a separately qualified narrow budget adapter can reuse the unchanged archive
code. All archives require reviewed/committed inventories before apply. Never
queue another lock user while an archive batch has live children. No current
task process is live at this checkpoint; inspect actual status before launching.
