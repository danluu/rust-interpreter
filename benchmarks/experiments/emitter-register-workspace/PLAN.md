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

Model01 debug: four controls pass; the set-reset test fails because its assertion
incorrectly requires a surviving member after clear. The captured sparse branch
also fails that same assertion. Close the attempt before changing it to require
all members absent. Add explicit callback visitation-order checking to the
existing filter test. The map/set implementation is unchanged. Model02 reruns
the failed debug command and the previously unstarted release command.

Model02 passes five/profile under49716/49719. Closer02 timed out on the shared
lock before touching source; closer03 under6688/6693 subsequently CLOSED it.
The staged integration drafts were prepared without changing frozen sources and
applied only after that closure. Stage2 connects only ordinary-region fact/set
storage, leaving transitions and other paths sparse. Bound all three dense maps'
combined payload to4MiB, with separate actual-capacity checks per allocation.

Seven controls/profile now include the existing five model controls, combined
allocation bounds, and exact sparse/dense staging across three programs with
joins, loops, long-region splitting, memory facts and assertions; both profile,
persistent-register and heap modes; six code capacities including zero. Compare
words, entries, resumes, assertions, operation counts and facts. This stage
changes production preparation storage but publishes/executes no native code.
Full controls and exact original saved-code reconstruction are still required.

Integrated01 stopped at debug compilation because an existing memory-operand
assertion compares live-in sets; the new wrapper lacked PartialEq/Debug. Preserve
and close that failure before adding cfg(test)-only content equality and debug
formatting. Do not derive storage/capacity equality or weaken the existing test.
The model's membership control now also compares dense and sparse sets directly.
Integrated02 repeats the failed compilation and unstarted release; no successful
guest or staging command is repeated.

Integrated02 passes seven controls per profile under38657/38661 at545a2cfd,
CLOSED58801 (child in terminal). Next reconstruct the two exact current adopted
unprofiled block/exhaustive captures via the existing saved-memory observer.
Verify all ordinary and scalar words against saved arenas, original operation
maps/assertions, and equivalent entries/resumes between ordinary and diagnostic
emission. Reuse the seven current controls without rerunning them. Two release
ignored observer commands; no guest execution or code publication. Preserve
reports before later validation, and close the original terminal before edits.

Reconstruction01 passes both current adopted captures at1bec189d:1050/1245
ordinary functions and60/69 scalar bodies;11,313,812/13,757,056 bytes exactly.
No new guests or code publication. Preserve76.42seconds setup in its receipt.

Next build01 runs the complete workspace in debug/release (minimum615 passing,
13 ignored per profile), complete Python suite (minimum456 discovered,22 skipped)
and the ordinary release VM build. Include the seven new named controls and
existing exhaustive scalar-copy test in each workspace result. Freeze sources;
retain all successful command logs and the built VM before publication. Compose
that VM with the exact adopted exporter/wrapper, under the tool-publication lock,
and record setup cost and immutable identities. No original workload latency
measurement in this stage. Strict121 fixture/cache/checking commands follow only
a closed successful build, before a prospective real-edit primary.
