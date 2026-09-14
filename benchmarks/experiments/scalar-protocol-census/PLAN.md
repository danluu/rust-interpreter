# Partition native calls on the adopted scalar runtime

The closed adopted-VM windows contain 409 / 440 native Call/Return samples.
The old protocol census predates scalar calls and understands only schema 1;
reusing it directly would either fail or label scalar transaction work as an
ordinary call prefix. Extend the test-only observer before drawing conclusions.

Add diagnostic span labels to scalar eligibility guards, private stack setup,
result checks, argument address/capture, native dispatch/status, restoration,
budget charging, padding clear, result publication, peak memory, successor and
private fallback. Labels emit no words and do not exist in the production VM.
Preserve ordinary frame/argument/return labels and the complete disjoint span
contract. Identify scalar argument indices explicitly.

Extend saved reconstruction to schema 2 by rebuilding immutable metadata and
exact native words for all captured scalar bodies before ordinary functions.
Never allocate or publish executable code. Reconstruct every ordinary function
and each transition, validate its exact same-process bytes and operation map,
and retain partial-window host/unresolved observations. Scalar body samples
remain separate; only native Call/Return self PCs enter this partition.

Run the two existing protocol controls plus a new scalar control in debug and
release. The scalar control covers zero/1/4/8/16-byte arguments/results, profiled
and unprofiled emission, and two fixed arena bases without executing code. Then
reconstruct the two closed captures and attribute all their transition samples.
Keep every failure and require exact counts and full byte reconstruction.

Use the ROOT-only shared target, two Cargo jobs, existing nonincremental/debug
settings, the shared lock, max(14 GiB, 8 GiB + twice allocated target) initial
admission and an 8 GiB child floor. This is diagnostic work with no guest
execution, performance measurement or change to the adopted runtime. Choose
the next production mechanism only after the current costs are partitioned.
