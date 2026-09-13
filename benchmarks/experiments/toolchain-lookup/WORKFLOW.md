# Prospective complete-command comparison

The candidate changes only launcher toolchain discovery: cached versus fresh.
All custom modes use tool49746a22 (the qualified integrated VM, exporter and
wrapper), identical strict checking, automatic function reuse, bytecode options,
standard-MIR identity and limits. The wide-operation VM is not part of this
comparison. Defaults stay unchanged while the candidate is experimental.

Run pgrust first, then private rg-aot and Nushell type-relations, with all three
mandatory regardless of performance outcomes. Each case has three cycles of
original, well-typed wrong edit and five cumulative valid production edits,
followed by compiled original-source restoration:22 states and132 commands.
Only the fifteen valid edited pairs enter medians. Preserve original assertions,
every A/A pair and all outcomes. No unchanged commands, retries for significance,
partial-pair substitution or omitted outliers.

Six modes: fresh baseline, fresh duplicate, cached candidate, ordinary native,
line-tables native and independent Cargo check. Rotate custom orders012,120,
201,210,102,021: all three positions occur five times over fifteen edited pairs;
each directed adjacency occurs twice per six-order block. Native mode order
and placement before/after the custom group alternate; check runs last.
All Cargo modes use two workers. Native libtest uses its ordinary default
thread count. Custom runs use two prepared workers, or one for the singleton
private selection; each test receives fresh guest state. The singleton is
selected by an exact checked filter. Runtime limits:100billion logical
instructions,150,000 allocations,64MiB memory and4096 frames.

Require the115-test launcher proof,20-command Cargo qualification and seven
comparison-driver tests before starting. Every candidate command after its
initial original state must report a cache hit. Initial lookup misses, native
compilation and empty target observations are retained separately; they are
not repeated cold-build measurements. Custom bytecode and entry catalogs must
match in every state. Invalid Rust must still be rejected before VM execution.

Primary pgrust: median paired wall improvement must exceed the observed A/A
wall envelope, and median CPU ratio must be<=1. Each mandatory guard requires
wall and CPU ratios<=1.05. Each case also requires A/A quality<=4% wall and<=3%
CPU. The A/A envelope is the largest absolute per-edit median deviation across
the three cycles; it is descriptive, not a confidence interval. No fixed8%
runtime-composition threshold applies to this independent launcher change.

Freeze script, workload, source revision, tool bytes, standard-library identity,
qualification and plan hashes. Use unique independent Cargo/cache namespaces.
Hold the shared benchmark lock throughout each case, with45-second admission.
Admission reserves8GiB plus six caches at120% of the recorded public cache
estimate; private admission reserves8GiB. Keep an8GiB floor before each command.
Do not change other workloads or clean private caches. Stop on unexpected
outcome, provenance, lock or storage failure; no automatic retry.

Publish paired total wall/CPU, A/A, native controls and nested lookup/Cargo/
frontend/lowering/VM stages. Keep private names, source, command text and Cargo
unit labels local; public summaries contain aggregate counts and ratios only.

The first driver-test admission timed out after45seconds with zero tests or
benchmark commands. Its receipt is preserved. A later read-only check found
the lock available; only the unstarted driver checks use a new02 run ID. No
completed qualification or performance command is repeated.
