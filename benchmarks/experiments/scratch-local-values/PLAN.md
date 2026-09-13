# Observe local values independently of virtual-register names

The native boundary memory bundle failed its primary screen and remains parked.
Start from adopted VMf0e5f2ea, whose exact captured maps and profiles are retained.
Do not carry over its wider clears/copies or paired-register source changes.

First measure a test-only hypothesis: an eight-byte local Load may be redundant
when x9 still contains the same value from a preceding local Load, Store or Copy,
even after the old virtual-register name is redefined. Existing forwarding ties
memory contents to that name. The earlier source-to-destination metadata-transfer
census found negligible coverage; this observes native bits without a new owner.

Track at most16 exact eight-byte frame ranges for x9. Typed emitter facts must
prove complete current-frame ranges. Capture only after instructions that really
leave the complete value in x9; never after a folded/static path that emits none.
Invalidate overlapping/unknown memory writes using the existing exact effect
rules. Preserve facts across an unknown write only when the existing immutable
guarded-range/disjointness proof already permits it. Never invalidate merely
because a virtual register changes its name or value.

A conservative instruction classifier discards all snapshots on any possible x9
write, branch/control transfer or unknown opcode. Only reviewed straight-line
instruction classes may preserve them. No extra native register, store elision,
replacement-policy change, instruction emission or guest execution is allowed.
Count only local eight-byte Loads not already forwarded by the adopted emitter.
Unit controls must exercise instruction classes, aliases, bounds, clobbers,
unrecognized operations and original machine-word identity.

Reconstruct existing unprofiled function bytes/maps exactly with observation on
and off. Join typed PC identities to saved exact logical profiles, keeping missing
functions and conditional coverage explicit. Profiling and captured ordinary
entropy may reach different paths. Report available-value occurrences separately
from machine loads saved or latency; do not infer speedup from the census. Only
sufficient coverage can justify a separately qualified runtime implementation.

Use the canonical lock,45-second admission, two Cargo workers,12 GiB initial
diagnostic-build headroom and8 GiB child floors. Preserve all historical code,
artifacts, source bindings, peer work, the independent cleaner and paused goal.
