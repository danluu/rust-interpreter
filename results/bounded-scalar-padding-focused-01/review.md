# Bounded padding: runtime proof and failure-path review

Reviewed candidatee0fa7f28 against52d13ae7. Only scalar commit clearing changes
in production; the other production edit passes the typed caller into that
emitter. Original general zero_range and ordinary Call clearing are unchanged.

Let D=gcd(caller.frame_align,max(caller.frame_size,1)). The initial caller base
and extent are both divisible by D. If a live end n is D-aligned, rounding n to
any validated power-of-two alignment H preserves it: H<=D leaves n unchanged;
H>D produces a multiple of H, hence of D. Induction covers arbitrary preceding
call histories. Returns truncate to the callee's saved base, so nested calls do
not add a different effect. Indirect calls and TLS callbacks use the same frame
reservation and truncation operations. Native reentry inherits that valid stack.

For the next callee alignment A, padding p=align_up(n,A)-n satisfies0<=p<A.
Both endpoints are multiples of min(D,A). D>=A proves p=0. Otherwise A<=16
permits only the subset of8/4/2/1 widths at least D; those bits sum exactly to p.
The emitted stores advance the cursor by their own width. A>16 retains the
original helper unless p is statically zero. Zero frames reserve one byte.

The existing alignment-add overflow, payload-add overflow, backing capacity,
register capacity, working-memory, frame-count and complete scalar instruction
budget checks remain before private execution. Clearing remains after scalar
success and its original logical charge, with no new failure or observable
write before commit. Scalar private failures still restore host state and replay
the ordinary operation. Peak memory uses the unchanged saved payload end.

The new helper uses only old scratch registers9/11 (and12 in the unchanged
fallback);3 and21 retain guest endpoints. Proven-empty emission leaves scratch
values untouched, which is safe: subsequent result copying reloads its operands,
peak accounting reloads9/10 and compares before csel, and profiling initializes
its scratch operands. No later operation consumes the old clear's condition
flags. Persistent guest pairs and host state remain preserved.

Evidence:21 focused tests passed in both profiles. New machine-code fixtures
cover exact store widths, unaligned host starts, empty and large fallback ranges,
whole-buffer dirty canaries, final cursors and live registers. New whole-VM
fixtures dirty ordinary backing through indirect calls, vary retained alignment,
commit scalar calls twice, read the resulting padding, and compare scalar JIT
with the interpreter at instruction/memory/frame limits, retaining ordinary-JIT
fault-order checks. Existing
scalar alias, private-fault, heap, profile and budget tests remain included.
The full workspace and five paired original-test profiles subsequently passed.
This establishes correctness evidence; adoption still requires performance gates.
