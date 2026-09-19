# Full qualification of exact short clear tails

Proceed only after short-clear-tail-focused-01 closes both seven-test native
profiles. Keep the same immutable two-file runtime diff against fca687eb.
Use its explicitly owned .work/short-clear-tail-runtime-build-01/target, not the
protected shared compiler target. This stage adds workspace test/link artifacts
to the runtime qualification cache. Record the broader scope explicitly.

Before each command retain max(14GiB,8GiB+2*target allocated) admission and the
3GiB allocated cap, with8GiB minimum free reserve. The cap's two-times allowance
reserves6GiB over the floor even though only about75MiB was allocated after the
first debug focused build. Stop between commands for reassessment if it grows
past the cap. No process control, storage cleanup or floor reduction.

Run the existing468 Python checks (22 skips), then full workspace debug/release
with two Cargo jobs/two test threads, and build the standalone release VM.
The expected workspace count is615 passed/13 ignored per profile: the unchanged
adopted614 tests plus the new native exact-cursor/register test. Bind every
source, source revision, dependency lock, controller and focused closure. Preserve
all results and failures; do not repeat passed children solely to repair reports.
Snapshot the qualified VM before subsequent target reuse.

An independent closure must verify every log, case count, command, source and
snapshot, owner and disk receipt. Native source remains experimental and no tool
default changes. Source build/setup costs remain outside performance ratios and
are separately reported. Next bind the unchanged qualified frontend to this VM,
run strict/cache/original guest profile controls, then the predeclared ES8 real
edit primary and held-out project guards.
