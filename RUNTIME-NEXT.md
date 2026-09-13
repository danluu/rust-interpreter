# Next work

The guarded-runtime campaign and complete-tool correctness qualification pass.
The exact qualified runtime/helper sources are published on main (`4dcc889`),
preserving the newer compiler work. Continue manual work with the goal paused.
[Integration and identities](results/guarded-ranges-main-qualification-01/assessment.md).

The selected-toolchain cache regression is fixed and passes 123 runnable root
checks, with 10 existing skips. Archived backend crates are not custom-tool
dependencies and remain excluded; explicit immutable tool keys remain usable.
[Cache fix](results/toolchain-cache-after-01/assessment.md).

1. Integrate the guarded local-value composition with current main compiler
   sources. All five gates and726 commands now pass:594 retained plus132 new
   Nushell commands, with zero repeats. Token improves4.73% wall/3.83% CPU and
   remains1.641 times ordinary native. Nushell is effectively unchanged against
   the prior custom runtime and passes its frozen guard. All9,005 final inputs
   verify and all114 original parser tests pass. Keep the16 MiB code default.
   Reuse the exact measured VM only after complete source identity checks;
   qualify newer exporter/wrapper/launcher code, original/wrong/restored project
   histories and the full parser before publication. No second timing campaign.
   Preserve the earlier admissions and verified cache-retirement evidence.
   The runtime is qualified for integration; the saved goal stays paused.
   [Primary](results/guarded-local-facts-edit-token-01/assessment.md),
   [Complete result](results/guarded-local-facts-full-continuation-01/assessment.md),
   [Original admission](results/guarded-local-facts-full-admission-01/summary.json).

The explicit 16/32 MiB parser screen is complete and the larger-capacity
treatment is parked: 0.69% paired wall improvement is inside 4.04% A/A variation.
All 32 controls pass, with five retained and 27 new commands after a documented
failed-test statistics repair. No unchanged full study will run. The earlier
profile reaches 66.60% of the large routine's bytecode; a typed check shows its
registers already avoid bulk initial zeroing. Broad reached-region compilation
and frame-clearing changes require further cost evidence. Keep the default
16 MiB and retain the prototype on its experiment branch.
[Capacity result](results/parser-jit-capacity-screen-continuation-01/assessment.md).

The previously adopted guarded-range result was a narrow2.55% primary wall
improvement, with the primary1.773 times ordinary native. Do not repeat unchanged
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
