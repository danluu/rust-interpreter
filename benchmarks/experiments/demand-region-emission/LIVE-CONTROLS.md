# First live demand VM qualification

Connect the qualified immutable plan pool, pending-edge transaction and stable
resume tables under explicit Limits.jit_demand_regions. Require full validation
and resumable JIT execution. Keep this code-generation choice fixed for a
PreparedJit owner. The CLI does not yet expose it, and demand code-dump requests
are rejected before execution pending an honest interleaved-region map schema.

Allocate/admit initial function metadata, block capacity and plans before table
publication. Per-function plan/metadata refusal reuses the immutable analysis
for eager emission; later fragment/edge refusal keeps the attempted region's VM
path. Bound retained plans and extra metadata separately at 16 MiB. Keep code and
resume-table budgets unchanged. Publish assertions and vacant resume slots only
after checked code/edge commit with all capacity reserved.

Prepare unattempted leaders before native lookup. After native execution returns
to another unattempted leader, prepare it before interpreting its first opcode.
Already attempted preflight/budget declines execute the existing VM tail. Update
per-PC profile block ends only on successful publication. Fixed per-function
register assignments never change with emission order.

Seven live controls compare complete original logical per-PC counts, results and
peak guest memory against interpreter and eager modes: loops/cold paths, every
small instruction-budget tail, guard declines, direct calls/returns with scalar
composition, prepared reuse across failures, forced retention/metadata refusal,
code budgets, explicit mode/partial-validation rejection, TLS teardown/reset and
nested callback calls. Equivalent existing memory-fault wording is normalized.
Run all 369 bytecode controls per profile and reconstruct both adopted eager
captures. Full workspace/strict qualification, interleaved diagnostics and original
project profiles/changed-source timing remain pending before any adoption.
