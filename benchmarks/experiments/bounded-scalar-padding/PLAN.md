# Bound scalar padding by layout, including every retained call history

The closed empty-work scope did not cover sampled ES8 padding. Its hot caller
has alignment16 and extent120, so the initial memory end is aligned to8. Every
successful direct/indirect call or TLS callback rounds that end to another
validated power-of-two alignment on return. This preserves its existing8-byte
alignment. A following16-byte-aligned call can therefore need only0 or8 bytes.

More generally let D=gcd(caller alignment,max(caller extent,1)) and A=callee
alignment. The live caller's memory end stays D-aligned under all such histories.
The next padding is zero if D>=A, otherwise a multiple of D below A. No CFG,
callee-effect assumption, branch probability or pointer-value hint is needed.
The existing alignment/overflow/capacity checks still precede clearing.

First qualify a bounded arithmetic and byte-store model, and join its eligible
sites to the four CLOSED typed scalar-entry reports and exact native self PCs.
Use A<=16 as the new bounded-store case; larger alignments retain the old helper.
Model zero frames using max(size,1), smaller/larger prior alignments, diverse base
addresses, and counterexamples for either missing hypothesis. Enumerate every
possible admitted padding and compare exact8/4/2/1 stores with a byte oracle and
dirty guards. Report all unqualified sites/samples and avoid timing predictions.

This is distinct from the parked general short-tail candidate: it removes the
chunk loop with a layout bound and removes impossible tail widths with the
preserved memory-end alignment. The general zero_range helper is unchanged.
Start with scalar commit padding only; ordinary frame clearing is out of scope.

If coverage is useful, qualify a separate runtime candidate in debug/release,
including machine-code canaries, retained padding, overflow/limit faults, exact
logical instruction/profile/entropy comparisons, full workspace checks and
strict type/borrow failures. Then one prospectively declared real ES8 edit screen
with baseline/duplicate/candidate/native/check. No unchanged retry of a parked
screen; promotion requires a passing screen and all held-out project guards.

Analysis uses12GiB admission and8GiB child/closure floors, shared lock45s. No
compiler or guest runs in this scope. Runtime qualification, if warranted, uses
the explicitly owned bounded target with3GiB cap and max(14GiB,8GiB+2*allocated)
admission, two workers, frozen source and independent closure. Protected target,
other sessions and paused goal remain untouched. Preserve every failed prefix.
