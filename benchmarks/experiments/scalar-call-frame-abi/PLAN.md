# Private scalar Call frame ABI

Start from the parked dead-register candidate 50fe7c9d. The width-alias candidate
is separately parked after its failed edited-source gate. Historical evidence is
retained; comparing those separate screens does not establish a causal ranking.

Keep the three live VM pointers in x0–x2 across scalar leaves. Captured argument
values and private Output use fixed caller-SP offsets; spill slots remain below
that SP. Read the original logical frame base in x21 and return status in x9.
Save/restore only x3 and x30 at the Call boundary. Retain every eligibility guard,
argument capture, whole-Call failure replay, padding zeroing, budget, peak-memory
and original-PC accounting rule. Decline before publication if SP-relative
addresses exceed the encoding's range. Give dead-register elimination the exact
return liveness for each convention. Keep the standalone scalar entry unchanged.

This removes six loads/stores and four argument-setup instructions per successful
native scalar Call. That is a static mechanism claim, not a timing prediction.
No additional graph pass, frontend change, bytecode format, guest backend, option
or default changes. Strict rustc type/borrow checking remains required. Tool and
JIT preparation costs stay inside the existing end-to-end accounting.

First run 21 focused controls in debug and release: existing full-VM transactions,
pressure, phi and failure cases plus a private-entry wrapper that verifies live
pointer/register preservation, all 64 argument slots, complete private Output
on success/failure, stack limits and original budget tails. Run all 597 workspace
controls in each profile (12 ignored), launcher/metrics checks and 121 strict
Cargo/cache commands. Reconstruct and compare six exact original guest profiles.
Then run the unchanged 40-command primary changed-source token screen. Preserve
the A/A wall envelope and CPU gates. A failed screen stops the candidate; only a
pass permits full token/folded/pgrust/private rg-aot/Nushell comparisons and the
114-test parser compatibility/edited-source checks. No timing-only adoption.

Use the shared lock, two Cargo workers, same-source shared target and conservative
14 GiB (or 8 GiB plus twice target allocation) admission. Never clean that target
or peer caches. All snapshot storage maintenance stays outside timing windows.
