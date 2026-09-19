# Diagnose current session input and constructor costs

Primary03 is closed and unmeasurable at wall A/A8.8%; no unchanged timing retry.
The retained twenty edited reports leave about40ms/request outside worker execution
and summed worker constructors34ms. Their scopes do not establish the cause.

Extend the existing diagnostic-only jit-preparation-observer feature with monotonic
phase boundaries: artifact read/hash, decode, catalog read/hash/decode/validation,
Program structural validation, report reservation; report serialization/write/hash;
worker setup before ExecutionMetadata and ExecutionMetadata construction. Keep all
actual checks and native admission unchanged. Timings include observer overhead,
are elapsed intervals rather than CPU, and may overlap between workers. Input and
output parts must sum exactly to their containing interval. Constructor parts must
fit the existing measured constructor total. Output counters are in the response
because report-write durations are unavailable before writing the report.

Qualify32focused controls in debug/release with both size-tier and diagnostic
features, then10session controls with only the size-tier feature;36owned sessions
and69clients reaped. Existing actual changed-input/report-hash/outcome controls
check phase conservation and bounds; feature-off controls require absent fields.
Freeze and retain every child. Replay16saved actual checked parser suites with
verification OFF for attribution. Earlier size-tier replay independently verified
all restored templates. Match all1,824original invocations, exact wrong failures,
current artifact sizes, kernel CPU and phase invariants; call hits observed.

Use shared lock45s,2workers, the existing shared build target never cleaned;
build max(14GiB,8GiB+2*allocated target), replay12GiB, child/closure8GiB. No compiler
or guest work outside qualified diagnostics, no adoption or benchmark claims,
subagents, goal calls, new services or peer process/worktree changes.
