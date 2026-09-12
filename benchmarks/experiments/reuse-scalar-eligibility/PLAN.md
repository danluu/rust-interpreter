# Reuse scalar visitor eligibility before frame planning

Unqualified candidate, recorded before source edits or measurement.

- Base: `8fa5c0fe6c00a82a908b11de326f7e32b4554300`.
- Branch: `perf/reuse-scalar-eligibility-20260912`.
- Owned worktree: `/Users/danluu/dev/rust-interp-build-plan-20260912`.
- No builds, tests, benchmarks or shared-lock acquisition by the implementer.

Packing and scalar promotion begin with identical primitive/ABI eligibility.
Their `Uses` visitors preserve eligibility for NonUse, Store, Copy and Move;
all other contexts clear it. Both use the same default MIR traversal. Save
packing's completed visitor result in a separate transient `Lower` field before
passing a clone into the frame planner. The planner can clear entry-live locals,
so its mutated eligibility must never become promotion's starting point.

Promotion consumes the retained visitor result after its existing local/code
bounds. Keep its original visitor builder as fallback when no retained vector is
present. Continue scanning aggregate assignments and call arguments for the
existing direct Copy/Move operand exclusions; these only clear bits and commute
with visitor exclusions. Do not change range merging or register promotion.

Retain eligibility even if planning declines for event/work bounds or does not
shrink the frame. The greater-than-4096-local packing early return remains, as
does promotion's matching local bound. `Lower::empty` initializes no snapshot.
Keep the vector separate from ChosenLayout because capture consumes that layout
before promotion. Serialized Observation/Template schemas and cache replay stay
unchanged; green replay bypasses both lowering passes.

Focused checks must compare both actual context policies, retain pre-planner
eligibility despite entry-zero mutation/planner fallback, and preserve direct
operand exclusions on cached and fallback paths. Root schedules compilation,
exact artifact comparisons, native-oracle checks and build-time measurements.
This removes recursive visitor work, not promotion's shallow exclusion scan.
No performance or adoption claim is made by this source branch.
