# Function analysis extraction preserves the adopted emission

All 345 bytecode library controls pass in debug and release, with the same
11 ignored observers per profile. The existing saved-memory observer reconstructs
both original adopted captures: 1,050 / 1,245 ordinary functions and 60 / 69 scalar
bodies. Every native word, operation-map span, assertion identity, resume entry
and existing memory partition agrees. No original project guest is rerun; the
native unit controls execute their synthetic cases as before.

The implementation moves read ranges, persistent liveness/assignments, fill and
call-slot hints and native leaders into an immutable FunctionAnalysis object.
Full-function emission still constructs and drops one analysis per compilation.
This is preparatory structure only: no plan cache, partial compilation, executable
patching, runtime option or measured optimization is enabled.

Setup takes 120.4 seconds across the four commands. Source and retained artifacts
are bound in the closure. Keep the runtime experimental while developing region
staging; the adopted immutable VM remains the benchmark control. Next expose a
single-region staging path and qualify its unresolved edges before any live
publication. Dense per-function temporary entry vectors are acceptable for the
initial offline equivalence model, but must be removed from per-region runtime
work before measuring a demand-driven engine.
