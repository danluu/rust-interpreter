# Native qualification scope

The [AAPCS64 SIMD register rules](https://github.com/ARM-software/abi-aa/blob/main/aapcs64/aapcs64.rst#612-simd-and-floating-point-registers)
assign v16–v31 to caller preservation. The existing region emitter reserves v16
for its guarded memory base and uses v0–v7 for wide transfers. This prototype
assigns complete values to v17–v31 only within one ordinary native region, under
the existing explicit scalar/resumable/persistent configuration.

Every emitted instruction updates temporary availability. Known SIMD loads and
captures invalidate their destination slot; unknown SIMD/FP instructions,
unreviewed SIMD memory classes and host calls clear all slots. A later reuse must
match its exact emitted producer, so skipped captures cannot expose old values.
Input address facts still prove complete active-frame extents. Copies preserve
overlap by using the earlier complete captured value and publish their destination
immediately. The ordinary x9 cache is never told a vector-only store changed x9.

Production writes direct numeric instructions. Before any new native execution,
a separate host-assembler test compares all capture/extraction/store encodings.
The assembler is a test oracle only. Concrete native fixtures then compare every
retained memory byte, heap byte, peak, readonly prefix and auxiliary charge with
the original interpreter at every instruction-budget prefix. Successful values,
logical counts and per-PC profiles must also match. Include narrow/high-lane
bits, unaligned overlap, unknown accesses, assertions, missing producers and
unexpected SIMD/call clobbers. Both persistent settings and profile modes run.

The first native controller runs the encoding test, then all 352 bytecode tests
in debug and release (11 retained ignored diagnostics). It retains failures and
does not execute project workloads or establish performance. Workspace/strict
qualification and original real-test profiles still precede the fixed primary.
