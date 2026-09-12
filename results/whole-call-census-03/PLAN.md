# Whole-call diagnostic

The two runtime experiments on exact integrated-tool artifacts failed their fixed
primary gates. Both remain parked. Inspect opportunities to remove entire calls
before selecting the next compiler experiment.

Use the exact original folded and token artifacts/profiles already bound by
`budget-register-smoke-05` and `call-slot-census-02`. Reconcile typed operations,
all native intervals, instruction/Call/Return counters and original receipts.
No guest execution, transformed artifact, timing claim or production change.

Count a narrowly provable forwarding form: one direct Call with arguments in
the same order and byte sizes as the wrapper ABI, then one complete copy from
a disjoint temporary to its result. All other operations must be Local or the
final Return. Exclude branches, effects, regrouped arguments, overlapping slots,
partial copies and cycles. Keep indirect identities/entries untouched.

Separately classify the existing leaf-inliner exclusions, retaining its 192-op,
512-byte-frame, 256-register, 128-byte-copy/ABI limits. Count leaves blocked only
by CompareBytes and/or the stricter block-local initialization proof when the
existing entry-prefix proof suffices. Report all other exclusions and the 50
hottest callees. These counts are necessary eligibility conditions: they do not
simulate caller placement, growth or resulting register initialization. The
caller-local coverage includes Local plus constant addition and is an upper
bound on the current inliner's narrower address analysis.

The diagnostic reuses the typed census implementation and its eight tests;
adds four proposal/classification tests and imports the exact register-analysis
source with its five tests. Freeze all sources, profiles, artifacts and commands
under the existing benchmark lock. Snapshot the diagnostic and preserve failures.
Select a bounded compiler change only after inspecting the full results.
