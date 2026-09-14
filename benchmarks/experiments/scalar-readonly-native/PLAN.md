# Native checked reads for scalar Calls

Start from the closed read-only value-model source. The preceding census admits
395 plans and covers 42 transition plus 53 body samples on the block capture,
with zero exhaustive coverage. These observations justify a prototype only.

The explicit scalar Call path retries a strict unknown-pointer-read decline
using the complete read-only proof, charging both attempts to its work budget.
Other strict declines retain their old path. The proof requires local writes,
bounded extents, acyclic scalar lowering, existing widths/shapes and no external
effects or callees. Keep every Read live and execute it at its original PC.

The private native Call ABI already saves pre-Call linear length at caller
SP+24 and preserves x2 (linear base), x7 (heap base), x8 (heap length). Select
the arena using the original low-usize address and check nonzero offset plus
the complete remaining extent before loading. The old linear length excludes
all fresh payload and alignment padding. Use only x9-x14 so x3/x15-x17 live
scalar allocations survive. Failed checks return private failure; ordinary
Call replay preserves original faults, side effects, limits and budgets.
No host callbacks or foreign guest backend are introduced.

Support all scalar read widths 1..16 with exact byte extents. Keep narrow loads
in the bounded dead-register pass as side effects. Standalone scalar emission
must reject Read nodes because it lacks the private Call memory context.
Preserve scalar profile counts, original result publication and shared arena
limits/reconstruction. No installed tool or main runtime changes at this stage.

Run the bytecode library in both host profiles: 359 passes and 12 explicit
ignored diagnostics per profile. New controls cover linear/heap boundaries,
all widths and budgets, dead-read fault order, padding/fresh-frame replay,
resource tails, result/source aliases, chained mutable input, high pointer bits,
register pressure, reconstruction and external-write rejection. Existing tests
exercise native code only in owned unit fixtures. No original project executes.
Preserve every attempted history; do not silently rerun a failed admission.

After correctness, count actual native emission against the same current sample
evidence, then build/qualify an immutable candidate and use the existing primary
changed-source screen. Adoption still requires all original strict/cache/project
and parser controls plus the full performance gates. No latency gain is claimed.

Hold the global lock; use the ROOT-only shared target and two Cargo workers.
Require max(14 GiB, 8 GiB plus twice allocated target) initially and the 8 GiB
child floor. Preserve peer work, installed tools, cleaner and paused goal.


The first 358-test/profile run passed, but source review found that heap-free
prologues do not initialize x7/x8. Preserve that run as incomplete qualification.
The second revision passes the program's existing heap ABI flag explicitly to
scalar emission. Heap-free bodies reject tagged reads without consulting those
registers; heap-capable bodies retain the checked arena selection. A new native
boundary and reconstruction control raises the expected total to 359/profile.


The actual native census admits 392 functions/409 callsites and verifies all 71
existing scalar bodies byte-for-byte. It covers 42 transition/52 body block
samples, none in exhaustive. The next immutable build runs 622 workspace tests
per profile (15 ignored, including the two added censuses), the full 429-test
Python discovery (407 passes/22 declared skips), and the release VM build. Keep
adopted tool df4006e0 as both compiler source and runtime control; retain its VM
and compiler binaries. Both later performance arms enable scalar Calls. This
new build installs a separately keyed candidate only after all checks pass.
