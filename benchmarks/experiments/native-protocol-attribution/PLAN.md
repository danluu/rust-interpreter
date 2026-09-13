# Refine the current native call/return sample

The adopted unprofiled block/exhaustive samples assign 433/499 generated self-PC
samples to complete Call/Return transitions (26.2%/34.7% of generated samples).
Before changing the protocol, partition its actual emitted instructions into
admission checks, budget charging, spills, frame clearing, argument/result
addressing and copying, frame bookkeeping, dispatch and failure paths.

Only test builds retain the new byte labels. Reconstruct every saved complete
function and operation map exactly, then reconstruct each isolated transition
against its captured bytes. Require contiguous full ownership of each transition
and matching resume entries. No executable allocation/publication or guest run.
Bind inputs to the original sampler receipts, source bindings, machine-code
hashes and successful assertions. Apply finer labels to the two saved sample
files only; keep ambiguous fine-label samples explicit and reconcile all 433/499
coarse transition samples. Do not equate static code size with execution time.

Run the bytecode test suite in debug/release with two Cargo workers and the
existing owned target. Serialize builds and offline analysis with the canonical
benchmark lock (45-second admission), 12 GiB initial and 8 GiB child floors.
Freeze source and command receipts; retain successful stages on interruption.
No production candidate, timing screen, service activation, or peer control.
Choose the next compatible optimization bundle only after the partition report.
