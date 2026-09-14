# Diagnose the parked read-only scalar candidate

The complete primary shows no end-to-end gain despite 7.73 million additional
scalar Calls in the block profile. Keep candidate cb47107b9d64 parked and main
on df4006e0. Larger comparisons remain cancelled.

Reconstruct all 199 saved profiled scalar bodies across the three original
captures before counting new-body live reads, packs, casts and arithmetic.
Join only exact original successful scalar PC counts. Separate previously
admitted bodies from read-only additions. Count repeated same-block read
identities, same-width casts and common address roots plus wrapping offsets.
These are opportunities for investigation, not proof of a valid address,
eliminable computation, hardware cost or a speedup. Do not infer failed private
attempt counts from successful-Call profiles.

The observer changes test-only code, emits into ordinary host vectors and
publishes no executable memory. One focused address-identity control keeps
wrapping arithmetic and rejects narrowing casts, joins, shifted slices, reads
and overflow results. Then run one bounded release observer on SHA-bound
original bytecode/maps/profiles. Freeze source, binaries/evidence and records.

Use the shared benchmark lock, two Cargo workers, ROOT sources and the protected
shared target. Admission is max(14 GiB, 8 GiB + twice allocated target size),
with an 8 GiB child floor. No timing benchmark, guest execution, compiler/Cargo
changes, foreign guest backend, host process control or goal-state change.
