# Next experiment: value lifetimes across native block edges

The ordinary native Call implementation misses the original gates: −19.3% paired
token command latency and +1.4% folded. Exact-code sampling of diagnostic tool
`7ad1ccdb` attributes 14.0% of token thread samples and 6.0% of folded samples to
direct register-array stores. Native zeroing loops occupy 11.7% and 8.2%; VM
frame reservation occupies 3.7% and 23.1%. These are perturbed windows, not savings
estimates. Large native byte-copy loops have little sampled weight. Do not start
another generic copy/opcode tuning series from these results.

The first implementation should address register lifetime and persistence across
native edges. The current two-slot cache discards facts at every region boundary
and conservatively stores cached values at exits. Native trees also cross those
boundaries. A per-function register assignment can remove repeated array traffic
while preserving the existing custom emitter and checked bytecode semantics.

## Bounded implementation

1. Add an exhaustive typed use/definition visitor shared with the current
   register-initialization analysis. Reads precede writes, including aliased
   Binary result/overflow registers. Direct/indirect Calls read destination and
   every argument register. Caller registers are not guest-addressable; callees
   can change guest memory but cannot alias the caller's register array.
2. Compute live-in/live-out sets with a predecessor worklist over the full
   bytecode CFG, including interpreted and short-region continuations. Return
   and terminal faults have no guest register successors. Bound analysis memory
   and work; a decline preserves the old emitter. Keep compile costs measured.
3. Start with at most three full u128 values assigned to x23–x28 as register
   pairs, uniformly throughout a function. Prefer values live across native
   edges, using static loop information and use counts. Do not infer zero high
   halves. Functions with no useful cross-edge values keep their old ABI/cache.
   This is the first persistent assignment, not a claim of a complete allocator.
4. External ordinary entries load assigned values from current register storage;
   linked entries preserve them. At a VM continuation, materialize every value
   live at that PC before returning. Budget declines and fallback branches must
   satisfy the same contract. An interpreted operation can change registers, so
   every new external entry reloads from the current storage.
5. Native tree functions save the parent's assigned machine registers, establish
   their own assignment, and restore the parent on every return/fault. Extend the
   current 64-byte internal frame with explicit saved-register slots; preserve
   the existing argument/result/profile slots. Ordinary wrappers need their own
   saved pairs and an original register-array pointer for exit spills because
   x0 becomes the return status. Keep both host frames correct on stub faults.
6. Route get/put/constant materialization and edge flushing through the assignment.
   Respect complete operand snapshots and result/overflow write order. Neither
   the old two-slot cache nor local-memory forwarding may retain a conflicting
   owner. A call invalidates memory facts while preserving caller register values.
   Dead registers need no public value, but every reachable VM/native read must
   see exactly the interpreter's value. Do not change instruction/profile counts.
7. Keep an explicit experimental option. Test ordinary loops, native-tree joins,
   both sides of branches, initially zero registers, high halves, far register
   indices, aliases, VM calls/returns, TLS, code-capacity declines, every relevant
   budget boundary and all native fault exits. Extend the assembly probe through
   x23–x28 as well as x19–x22, LR, SP and 16-byte alignment. Run optimized checks
   before the saved original artifacts and repeated real edits.

Keep `b2aa6efe` as the primary comparator; use `2f31c6a0` only as an intermediate
comparison. The original targets remain 20% lower paired complete token latency
and 10% lower folded latency, CPU improving too, followed by the seven held-out
workflows and broader native/TLS/fre execution qualification before retention.
Do not reset the targets to excuse another intermediate gain.

## Frame lifetime work remains separate

Frame clearing is particularly costly in folded. The older typed census already
found that argument copies overwrite only 4.4% of its cleared bytes and 9.1% of
token's; argument-only elision was correctly parked. The MIR inventory also found
limited weighted savings from merely dropping unused locals. Repeating those
experiments is not the next step.

Larger reductions need lifetime-based aggregate stack-slot reuse or a proof that
specific bytes are written before any possible read/escape. Preserve caller
argument-copy ordering, unknown aliases, frame padding, Return reads and guest
bounds. A callee can observe parent memory through pointers, so a local-only
write scan is insufficient. Do not silently replace the current zero-initialized
bytecode contract with uninitialized storage. This should be a separate compiler
experiment with changed-artifact controls when layout changes, not an unmeasured
addition to the register candidate.

[Measured gates](../../../results/native-region-e2e-01/assessment.md) ·
[Token attribution](../../../results/native-code-token-sample-02/generated-attribution.json) ·
[Folded attribution](../../../results/native-code-folded-sample-01/generated-attribution.json) ·
[Argument-zeroing census](../../../results/frame-initialization-census-01/summary.md)
