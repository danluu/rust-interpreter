# Scope local writes overwritten before observation

The pointer-slot initialization extension adds no clearing samples and is parked.
Prior copy-equality and reserved-payload models are also parked. This distinct
question is whether a Store or Copy writes temporary local bytes that are fully
overwritten before any read or possible fault, in the same native region.

Use only the independently closed adopted-hot-loop-census-02 inputs:1933/1429
saved generated samples, exact native region bounds, rendered operations and
separate fixed-entropy logical profiles. No guest, compiler, timing or code
publication. The rendered-operation reader estimates scope; it is not a typed
production proof and must not drive native emission.

Track at most128 pending writes of at most128 bytes. A prior write becomes a
candidate only after every byte it wrote is overwritten. A read of any still-
needed byte rejects that pending candidate. Copy reads its complete source
before writing, including overlaps. Local ranges must fit the frame completely.
Unknown reads/writes, assertions, division, calls, unmodeled operations and exits
end every pending proof. Zero-byte accesses still require a proven local address
because invalid pointers can fault even without a data transfer. Only exact Local/Imm and reviewed nonfaulting integer
binary operations retain address facts; register outputs kill old facts. Native
regions start with no facts or pending writes. Capacity loss discards candidates.

Twelve controls cover complete/partial overwrites, reads, overlapping copies,
zero lengths, capacity, local bounds, register aliasing, arithmetic, fault/exit
barriers and region separation. An independent concrete-byte oracle checks2000
seeded40-event traces (80000events): suppress all proposed writes together and
compare every explicit read, every barrier's full memory and final memory with
the original execution. It does not reuse the analysis transfer functions.

The saved-data report must reconcile all Copy/Store samples, assign candidates
by exact function/PC, and separate cyclic samples from other regions and logical
counts from sampled windows. Full operation samples are only an upper bound;
unchanged address checks, caches, profile counts and budget-tail behavior still
need typed/emitter/native qualification before any production implementation.
The independent closure recomputes both complete derivations and checks sources,
terminal, logs, controls and every bound input. Preserve any failure and do not
rerun an unchanged successful stage. Shared lock45s, analysis12GiB, children8GiB.
