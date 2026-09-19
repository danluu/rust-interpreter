# Census implicit zero high words and interpreter repair costs

The closed consumer-only proof covers33/13 sampled upper stores, too little for
an isolated implementation. This diagnostic sizes a broader representation for
registers whose every possible definition has a zero upper64bits. Reuse the
existing bounded register_widths::prove; initial logical values are zero and all
unknown/wide definitions decline. The proof alone does NOT validate stale stored
upper words. It can support a design only when native high reads synthesize zero
and the interpreter restores the same logical values before any full read.

Before any implementation, count exact captured high loads/stores for those
registers and separately bound interpreter repair traffic. Validate both current
adopted profiles against typed bytecode identity, code and counter shapes. Count
all interpreted narrow read operands, including already-masked consumers; also
report distinct narrow registers per interpreted instruction. This deliberately
overstates a possible selective repair requirement and is not elapsed time.
Scalar/native hits never become interpreter work. Keep counts of native entries,
interpreted instructions and candidate native accesses in their original scopes.

Run the four unchanged width-proof controls and three new profile/cost controls
in debug and release. Retain the independent traffic assembler object and run
its six controls. The observer validates one saved artifact and two profiles;
it never executes a guest or publishes native code. Join widths to the two
closed same-process captures, reconcile all samples, and retain ambiguous PCs.
Production representation, initialization and every emitter remain unchanged.

A future implementation must handle all native entries/exits, VM read roles,
reused/mixed-width frames, callbacks, partial failures, limits and profiling.
Never remove stores while leaving stale high bits visible to full-width reads.
Include actual preparation/repair cost in the existing edited-source benchmark
gates before adoption. This census alone admits no runtime change or timing.

Use the root lock with45-second admission, two Cargo/test workers, the existing
owned target and max(14GiB,8GiB+2*allocated-target) build admission. Offline floor
12GiB and child floor8GiB. Preserve all closed captures, peer sessions and paused
goal. No new AWS service, alternative backend or changed benchmark workload.
