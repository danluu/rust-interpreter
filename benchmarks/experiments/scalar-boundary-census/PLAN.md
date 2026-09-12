# Typed scalar boundary census

Diagnostic only, based on integrated source `5b2330c` / tool `9637b0ac`.
Copy the qualified VM and wrapper unchanged; rebuild only the exporter with a
bounded observer. Do not modify guest operations or the production source.

Capture typed MIR arguments/results before scalar promotion. Reuse the actual
promoter's use-context visitor and call/aggregate operand exclusions. Record
primitive type and rustc `BackendRepr::Scalar` classifications separately.
Reject overlapping storage, unsupported widths, spread arguments and ambiguous
ABI bindings. Synthetic caller-location slots remain explicitly uncovered.
The first smoke caught a wrong assumption: dedicated ABI storage can move during
aggregate relocation. Rebind at that exact pass boundary by preserved ABI
argument order/width and result width, then require unchanged slots through all
later passes. Keep captured offsets separately; unbound spread/zero arguments
have no final slot. The failed export ran no guest code and remains recorded.
Ordinary private primitive counts are descriptive; their offsets can move in
the subsequent aggregate relocation and must not be matched to final PCs.

Bound each body to 4,096 locals / 100,000 lowered operations, and the collection
to 32,768 boundary rows / 10,000 functions. Record exhausted bodies explicitly.
Bind observations to numeric function IDs, final ABI slots and SHA256 of bincode
serialized final Functions. Pretty names are not identities. Final JSON is
limited to 32 MiB. An ABI mismatch fails the observation rather than guessing.

Qualification: exporter tests including overlap, width, bounds, ABI identity and
privacy-reason checks; fresh original folded/token exports and original test
assertions. Both artifacts must equal the exact integrated artifacts. Reconcile
only their original exact profiles using typed operations, with explicit unknown
address/coverage accounting. Counts cannot establish a speedup.

Host-build admission: 12 GiB free, including the existing 8 GiB floor and 4 GiB
allowance; two jobs, locked/offline. Serialize builds and executions with the
shared benchmark lock; record owned processes and preserve failed runs. Use the
actual new exporter's capability probe at publication. No timing gate is being
changed. A subsequent implementation requires its own frozen plan.
