# Allocator transition scope does not justify a native bridge yet

The adopted complete profiles contain885372,1572514 and74906 interpreted allocator
operations in the three original assertions. These are frequencies, not elapsed
cost. C allocator variants have zero dynamic executions in these profiles.

The current partial unprofiled windows contain only2 allocator-adjacent generated
samples for block (one exit/flush, one entry) and0 for exhaustive, out of1933 and
1429 generated samples. Broader native-boundary buckets have39/33 self samples and
other-host buckets27/32; neither is allocator-specific. Heap-context73/155 samples
would remain work inside the host allocator and cannot be counted as removed.

Defer native allocator bridging. This evidence does not establish enough removable
work to justify a new host-call ABI, heap-base refresh, register preservation and
exact error/budget proof followed by another runtime campaign. It is not a claim
that the bridge cannot help: the samples are partial and hardware stalls are not
attributed. No guest, compiler or performance measurement ran in this census.

Next inspect current whole-process retired instructions/cycles against the native
original assertions. The old7.13x instruction result used runtime49746a22, so it
must not be presented as current df4006 evidence. Reuse the preserved local counter
launcher only after exact source/binary provenance and fresh API controls. No
privilege, counter configuration, attachment or out-of-scope process control.
Any diagnostic result remains separate from whole changed-source acceptance.
