# Reuse owned program storage during bounded leaf inlining

Prepared before production edits or measurements. Candidate is unqualified.
Base: b7673351facfb3a769ffa83265e0187fa3a680e7, branch
`perf/owned-leaf-inline-20260912`, owned worktree
`/Users/danluu/dev/rust-interp-build-plan-20260912`.

`optimize_calls` owns its Program, but invokes the borrowed leaf inliner. The
current implementation clones the complete Program before scanning callers,
including data/statics and every unmodified function's bytecode and diagnostic
strings. Expanded callers then replace their already-cloned code, and rejected
expansions clone the original caller again. This candidate removes that copy
from the owned export pipeline without changing inlining policy.

Share one preparation worker between the existing borrowed API and a private
owned worker. Preparation validates the original program and options in their
current order. It computes eligibility, diagnostics, local-site proofs, budgets,
branch relocation, fallthrough-jump removal and caller initialization guards
against an immutable original graph. Accepted replacements are accumulated in
original function order; rejected expansions restore all budget counters and
do not retain a replacement. Each replacement clones only the changed caller's
name and argument metadata, using its newly constructed code directly.

Only after all decisions finish may a common commit stage install replacements.
The borrowed API clones its input for that stage and leaves the caller's input
unchanged. The owned worker moves the original Program into that stage and keeps
all unmodified Function/data/static/metadata allocations. Final program
validation, operation counts, JSON field/report order and errors remain the
same. `optimize_calls` changes only which leaf worker receives its owned Program;
both forwarding passes and timing boundaries remain in the same order.

In particular, a caller expanded earlier in function order must not become a
new leaf for a later caller during this pass. All Local extent queries must use
the original callee layout, even when that callee also has a replacement. The
owned worker is not a new public API and does not change serialization or VM
execution. No unsafe code, persistent cache, policy threshold or target-specific
case is introduced.

Focused tests will compare serialized programs and full JSON reports from owned
and borrowed entrypoints, exercise invalid-program/options ordering and existing
growth/initialization guards, and include crossing caller/callee edges. Tests
will also check that successful owned transformation retains the allocations of
unmodified functions and Program storage, proving that equivalence is obtained
without merely routing the owned path through the original full clone. Existing
native-oracle execution tests continue to cover inlined argument aliasing,
branches, loops, zero-sized values, faults and exact limits. Composed forwarding
tests compare the owned pipeline with the original borrowed-pass sequence.

No builds, tests or performance commands will be run by the implementing agent.
Root will schedule qualification and predeclare measurement gates. This changes
the bytecode library, so a compiler build may also change the VM binary hash;
build-time qualification must retain the already-frozen VM independently.

Tradeoffs: accepted replacements retain their new code until all decisions have
completed, alongside the original graph. The old borrowed pass already retained
original and output graphs; the owned path now avoids the full cloned graph.
Changed caller names/argument vectors still require small temporary copies.
The borrowed API continues to require a complete output copy by its contract.
It now clones after preparation, so its peak temporary allocation can include
all prepared code plus the just-cloned original code before replacements are
installed. Qualification concerns the owned compiler pipeline; no borrowed-API
performance improvement is claimed.

Implementation review: benchmark_review found no production-source blocker.
The five new focused tests include a literal scarce-budget rollback report;
borrowed/owned parity alone shares the preparation algorithm and is not treated
as an independent semantic oracle. Existing scalar and aggregate fixtures now
exercise the owned result while checking byte/report parity with the borrowed
API. No execution or timing has occurred during implementation.
binary_codegen independently checked the focused test fixtures and exact
rollback counts, including nonzero diagnostic rollback, with no source blocker.
