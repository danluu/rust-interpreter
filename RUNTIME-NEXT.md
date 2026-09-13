# Next work

The guarded-runtime campaign and complete-tool correctness qualification pass.
Publish the exact qualified runtime/helper sources and evidence to main, keeping
the newer compiler work. Continue manual work with the saved goal paused.
[Integration and identities](results/guarded-ranges-main-qualification-01/assessment.md).

1. Verify the automatic tool-build fingerprint covers every local workspace
   dependency and the pinned toolchain. Inspect existing tests before changing it;
   a stale tool after a shared-crate edit would be a correctness issue.
2. Qualify the drafted complete pgrust `gram_core` support probe: one ordinary
   unfiltered native library command, then the exact same original test bodies
   through the normal custom launcher. Static inspection finds 114 tests; actual
   inventory/support is unverified. Preserve every assertion and report failures.
   Native defaults use line tables and disable incremental compilation. Any
   subsequent warm timing needs explicit matched incremental controls.
3. Use the actual emitter to count local-value forwarding blocked by writes
   whose new guard already proves disjoint from the current frame. Reconstruct
   saved baseline code exactly before comparing a test-only alternative. Count
   lost forwarding, spills and flushes too. Static words are not retired
   instructions or latency. Choose an implementation from that evidence.

The current five-case result is a narrow 2.55% primary wall improvement; the
primary still takes 1.773 times ordinary native. Do not repeat unchanged
candidates or infer general large-project speedups. Primary screens reject weak
new mechanisms before full histories; every adoption guard remains mandatory.
Keep allocator/arena redesign and broad lazy-MIR work conditional on evidence.
The other Rust session owns its compiler/Cargo investigation; preserve its work.

Qualified source/correctness proofs may be reused only after exact identity
checks. New compositions need strict errors, original tests, wrong edits,
restoration and complete-command measurements appropriate to their mechanism.
Keep source pins, explicit workers/limits, private-data redaction, shared-lock
admission and conservative disk floors. Do not control unrelated processes,
reactivate the goal, use subagents, or activate AWS offerings.

[Suggestion decisions](docs/SUGGESTIONS-REVIEW-20260912-2210.md),
[full comparison](results/guarded-ranges-admission-resume-01/assessment.md),
[prior work snapshot](docs/history/RUNTIME-NEXT-20260913-before-guarded-integration.md).
