# Owned replay proposal with unrun Rust equivalence tests

This successor preserves the initial `hir-owned-replay-01` proposal and targets the
same immutable options-hash compiler `4de35bdacef0e3cd18a66bc30b5459c19e09b118` at
`/Users/danluu/dev/rust-interp-runtime-exporter-20260918/.work/hir-options-hash-compiler-01/source`. No checkout was changed and no compiler, Rust parser, test, provider,
probe or benchmark was run. The six added Rust tests are source proposals only.

The implementation is byte-identical to proposal 01 outside the added test items
and regenerated source identity. The old cross-Current `prepare` API, all four
existing prepared.rs tests, `validate::check`, ReadyHit construction, replay_plan,
commit trace, recapture and poststate checks remain unchanged. The owned warm
path retains complete validation against its one immutable Current and moves the
checked raw tree after conversion; it removes only the second validation and two
raw-tree clones. Allocation failure timing can change. The ownership rationale
and recorded profile limitations remain in the original README/provenance.

`test-additions.rs` is the exact fragment inserted into the existing prepared.rs
test module, not a standalone test or alternate AST implementation. It calls the
real existing `validate::tests::tree`, `checked`, and `current` helpers and the real
journal validator. The reference result is the previous `validate::check` then
`prepare` sequence; any acceptance mismatch fails. Accepted fixture values are
compared for Current identity, expected raw tree, owner and ID range, source range
and text, prefix map, root/block/tail IDs and spans, block flags and integer value
and suffix. This deliberately compares the existing block/integer fixture shape;
it does not claim complete ExprKind or real HIR materialization coverage.

Six added test methods cover:

- Valid owner, ID and absolute-source rebasing, including the exclusive INVALID
  endpoint, highest representable source extent, and Dummy root spans.
- Invalid current ID/source ranges, resolution/reference lengths, extra locals
  and current kind mismatch.
- Valid unused prefix binding plus foreign-owner, stale/missing resolution and
  wrong/missing reference rejection.
- A separately valid swapped-origin journal paired with the fixture's original
  origin map/tree. Current-state checks accept; full order validation rejects.
- Duplicate/missing/out-of-range nodes, wrong root, invalid UTF-8 span boundary,
  source overrun and reversed range rejection.
- The maximum u128 literal, overflow and wrong integer suffix.

The full patch is against the original compiler, not against proposal 01.
`tests-added.diff` isolates the test addition from proposal 01. All 25 acyclic
identity members and source_identity.rs were reconstructed in memory from exact
preimages. New source identity: `8946102708c589586d3be0169b409e4465b43c2d2498ab61aa26c125ecf22099`. Provenance records every
before/after hash, initial-artifact identity, preserved evidence reference and
strict hunk readback. All original source/evidence inputs and all three initial
proposal files were rehashed before and after generation.

Before adoption, compile this candidate and run all inherited lowering,
interface/support/run-make, cold/warm, corruption and stale-current controls,
including these actual Rust tests. Qualify real unchanged/edit/restore diagnostic
and RBC equivalence, failure behavior, trace/recapture and finalization. Unit
fixtures alone do not replace that work. No numeric speedup is inferred from the
overlapping saved profile spans; current options-hash runtime/Ruff work stays first.
