# Bounded emitter register workspace

Closed preparation-phase-workloads-refined01 identifies ordinary region
construction as the dominant preparation stage. Earlier offline emission stages
agree. Broad and conditional demand-region candidates both failed their real
edit gates; liveness-only work is too small. Do not retry those mechanisms.

Hypothesis: temporary ordinary-emitter facts, definition sets and live-in sets
can use dense indexed slots instead of allocating/searching BTree nodes for each
region. Reuse one bounded workspace within each function, clearing only touched
registers between regions. This is host preparation storage only. Preserve exact
fact values, sorted flush order, machine words, budgets, assertions, code capacity,
publication, guest state and all checking. No persistent cache or relaxed types.
No speedup is claimed from the diagnostic phase totals.

Stage1 is a cfg(test)-only generic map/set model, unused by any emitter path.
Dense allocation requires at most65,536 registers and4MiB of actual Vec payload
capacities per map, excluding allocator overhead. Reserve buffers fallibly and
fall back to the existing sparse map on rejection/allocation failure. An
out-of-range insert also preserves all current values through sparse fallback.
The production integration must separately bound combined workspace allocation;
per-map bounds are not a combined-memory promise. Zero-size/large declarations
use sparse storage. Removed/reinserted keys touch once; clear resets both data
and membership without losing capacity. Filtering visits keys in ascending order.

Five controls compare deterministic generated operations, adversarial insert/
remove/filter order, reset/reuse, declared bounds, outside-range conversion and
set behavior against standard ordered collections. Run debug/release with two
workers on the root target only. This stage publishes no executable guest code
and runs no workload. Future integration requires exact saved code reconstruction,
full controls/strict outcomes and a prospectively declared genuine-edit primary.

Root lock45seconds. Build floor max(14GiB,8GiB+2*allocated root target),8GiB
before children/closure. Freeze exact sources and evidence; close each attempt
before correction and preserve completed commands. Never clean the root target
or alter peer/private work. Saved goal stays paused; manual work continues.
