# Integer helper inlining paused

This one-attribute runtime candidate adds `#[inline(always)]` to `binary()`;
its body and arithmetic semantics are unchanged. All 297 workspace tests pass
in debug and release (one ignored). Before runtime timing began, the user
redirected ongoing work to build-time improvements. No performance comparison
was run, and no gain, failure of a performance gate or runtime qualification
is claimed. The candidate is parked on a local experiment branch and is not
merged to main. Source snapshots, test receipts and the original prospective
plan remain preserved in [qualification.json](qualification.json) and
[predeclared-plan.md](predeclared-plan.md).
