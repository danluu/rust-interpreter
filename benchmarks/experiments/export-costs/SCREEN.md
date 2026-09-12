# Edited end-to-end screen for persistent function reuse

First require 51 debug/release exporter tests (including exact legacy cache
bytes), 337 complex fixture commands, 293 semantic-edit commands, 98 cache
fault/publication commands, and the exact eight-state production history for
the selected case. This includes actual skipped lowering, not just replay
verification. Freeze the qualified binary and all launch adapters before timing.

Screen fre tokenization first against the retained full-workflow tool
`9637b0acb1d208524c3c8b446af64cfd5e2d0d3be75e1412a8df76750ce36223`.
Use the original workflow's five production edits and assertions, one cycle,
balanced mode order, separate cold Cargo caches, native control, independent
Cargo-check control, wrong-edit rejection, and matching executed bytecode.
Reuse is enabled only in the candidate Cargo child. The candidate includes the
hardware SHA backend and bulk cache bytes; this is a combined build-time
candidate, not an isolated estimate of caching alone. The VM/wrapper remain
the retained binaries. All command time, including cache work, is included.

The cheap continuation gate is a median paired edited wall-time ratio <= 0.92
and CPU ratio <= 1.02, with all correctness and provenance checks passing.
Cold results are reported separately. An unchanged build is never a sample.
This one-cycle screen is not confirmation or a confidence interval. If it
passes, run folded and large frontend-heavy holdouts before a fresh three-cycle
confirmation. A failed candidate is not retimed to seek a passing result;
use the recorded costs to choose a materially different boundary or approach.

The supervised driver records the exact benchmark command and candidate
launcher substitution. It validates the saved cache counters from every
candidate compile outside command time. A conservative 2 GiB growth allowance above the 8 GiB running floor
covers native/check metadata, two custom targets, bounded function-cache
generations and saved artifacts for this single-cycle library screen. Do not
start below admission; record a failure before source mutation if space is low.
