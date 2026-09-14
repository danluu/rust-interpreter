# Bound the opportunity for runtime scalar lowering of confined leaves

The heap-address candidate failed its full token wall/CPU gates. Its source and
all evidence are parked. The immediate-word census covers only 8 / 0 removable
sampled PCs and is deferred. Work here starts from main f1b89482 without either
candidate. The historical V6 scalar ABI is also parked: execution savings were
largely consumed by new exporter work. Do not rerun that candidate unchanged.

Before another runtime implementation, join the existing typed CFG memory-
confinement and initialization proofs to the exact adopted call-cost reports.
Retain only no-direct-call functions with a proved confined body and initialized
reads. Report an additional bounded subset (frame <=512 bytes, <=512 operations,
<=512 virtual registers). These generic limits size a potential small-function
JIT tier; no names, profiles or project-specific patterns select production code.
Match exact IDs, names and frame layouts. Preserve all declined categories,
logical incoming calls and separately scoped call/return samples. Whole-function
logical operation counts are not per-call costs or retired instructions.

This is only an upper bound: argument/result scalar widths, register allocation,
address escape, complete CFG lowering, aliasing, fault-state materialization,
assertions, budget tails and compile cost still need a new runtime contract.
Confinement permits explicit Trap/Assert paths; it does not prove infallibility.
Any future scalar tier must preserve entry checks, ordered argument copies and
partial failures, peak memory and frame accounting, arbitrary return pointers,
strict checking and exact original logical profiles. A decline before progress
uses the existing interpreter/JIT path. No V6 compiler change is proposed here.

Use only existing completed typed reports, sample/call reports and their closed
proofs. No Rust build, guest execution, code publication or timing experiment.
Run focused identity/partition controls first, then this small JSON join under
the shared lock with 45-second admission and 10 GiB free space. Record hashes,
Git source, ownership and the supervised terminal result. Preserve all earlier
experiments and other sessions. A useful bound is a reason to design the proof,
not an adoption result or expected speedup.
