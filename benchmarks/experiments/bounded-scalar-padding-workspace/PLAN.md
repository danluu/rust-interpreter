# Full workspace validation of bounded scalar padding

Start from closed focused01:21 exact tests in both profiles. Run all Python
workflow tests, all workspace Rust tests in debug/release, then build and copy a
standalone release VM snapshot. Use the same explicit bounded runtime target,
3GiB allocation cap and max(14GiB,8GiB+2*allocated) admission before/after every
child; shared lock45s, two workers, offline locked dependencies. Preserve all
prefixes and close independently; no source/controller edits before closure.

The former short-tail workspace had609 passed/13 ignored, including its one
candidate test. This source restored that test away, added one current-protocol
test, two scalar empty-work model tests and two bounded-padding tests:613 pass.
The scalar-entry metadata observer added one ignored test:14 ignored. The
current-protocol observer replaced its previous ignored implementation.
Python remains468 discovered/446 passed/22 skipped. Verify named critical tests
as well as complete unfiltered command and counts; preserve discrepancies
without replaying passed commands to repair reporting. No original-project guest
or timing command runs in this stage. Default and protected target unchanged.
