# Runtime lookup comparison

`baseline_runtime_compiler.py` preserves the loader from `1103312a`.
`measure.py` selects that module or the candidate and times the normal immutable
runtime/std lookup on the existing installed runtime. Both arms retain every
validation and must return identical installation identities.

`plan.json` fixes the 22-test control suite, two warmups and twelve alternating
pairs before execution. `inputs.json` freezes all producers and the actual
runtime/std manifests. The controller holds the canonical lock throughout and
keeps every child receipt and raw output; failed controls stop the comparison.

The initial cProfile diagnosis and complete comparison evidence are retained in
[the result](../../results/runtime-lookup-paths-01/README.md). This measures a
launcher component, not edited application builds. The absolute-path plan is a
record of this run, not a portable installation recipe.
