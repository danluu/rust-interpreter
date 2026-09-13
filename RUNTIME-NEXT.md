# Next work

The guarded-runtime campaign and complete-tool correctness qualification pass.
The exact qualified runtime/helper sources are published on main (`4dcc889`),
preserving the newer compiler work. Continue manual work with the goal paused.
[Integration and identities](results/guarded-ranges-main-qualification-01/assessment.md).

The selected-toolchain cache regression is fixed and passes 123 runnable root
checks, with 10 existing skips. Archived backend crates are not custom-tool
dependencies and remain excluded; explicit immutable tool keys remain usable.
[Cache fix](results/toolchain-cache-after-01/assessment.md).

1. Implement and qualify an explicit bounded JIT code-limit option, preserving
   the16 MiB default. The publication audit for capacity and environment support
   passes: all40 existing project edit controls preserve exact artifacts/outcomes. The
   full114-test parser comparison is15.78% slower than native under repository
   settings and23.03% slower with matched incremental compilation. Preserve the
   original22-command identity failure; paired traces locate its constant split
   in rustc with template reuse disabled. The separately revised66-command
   comparison keeps A/B identity within each cycle/state and all native outcomes.
   The dominant reference-vector test's missing routine needs16,554,488 native
   bytes by itself, exceeding remaining arena space. Compare16/32 MiB on complete
   changed-source commands before investing in reached-region compilation.
2. Use the actual emitter to count local-value forwarding blocked by writes
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
