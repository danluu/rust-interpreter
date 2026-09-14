# Resolve scalar-frame candidates at original bytecode PCs

Start from the closed confined-leaf census, on main's runtime. No compiler,
artifact, interpreter or JIT behavior changes here. The parked V6 scalar ABI
added exporter cost; this investigates a separate runtime preparation plan.
The earlier bound includes 11.2M / 16.4M direct native calls, but is not a scalar
eligibility or speedup proof.

Reuse the qualified bounded typed CFG confinement/initialization solver in an
isolated diagnostic package. Keep its ten controls and 6,400-path byte oracle.
For a small leaf (frame/operations/registers <=512, no direct/indirect calls,
argument/result widths 0/1/2/4/8/16), solve confinement from PC zero, then replay
all reachable blocks from converged states. Resolve each exact memory read/write
range, including constant dynamic extents and Copy's read-before-write order.
Report zero-length accesses without claiming a valid pointer; include Return
and explicit Assert/Trap sites. Preserve every original PC and function identity.
Require the separate initialization proof. Bound both solve and replay work.

This phase produces access metadata, not executable scalar code. In particular,
confinement does not prove that Local-derived address bits cannot escape in a
result. Argument overlaps, cross-slot accesses, raw returns into the new frame,
all fault snapshots, instruction-budget tails and native admission fallback
remain mandatory obligations before code generation. Report scalar-boundary
rejections and access widths so a later plan can be chosen from actual coverage.
No whole-frame clearing elision or generic scalar ABI is enabled by this report.

Run the old oracle and focused annotation controls in debug/release. Build one
owned diagnostic binary and analyze only the pinned original token artifact;
join its typed IDs to the two existing whole-test profiles/call reports. No guest
executes. Use two Cargo workers and the shared lock with 45-second admission.
Build admission is max(14 GiB, 8 GiB + twice allocated shared-target bytes), the
previous conservative setup rule; the target is reused at the same source root
and never cleaned. Preserve all inputs, setup time, failures and child receipts.
