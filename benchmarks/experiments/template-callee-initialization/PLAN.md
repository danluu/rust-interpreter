# Bind callee register initialization in the native-template key

Code review finds a missing derived emission input: resumable_call embeds the
callee needs_initial_zeroes result, while CallInput currently binds only layout
and scalar-entry properties. Changing callee code can change that result while
leaving the caller bytes and key unchanged. This is an experimental cache
correctness issue; the adopted runtime has no cross-program template history.

First preserve two failing controls against the old key: unchanged layouts but
changed register initialization must miss in both relocation modes; actual reused
caller code must agree with fresh JIT and interpreter after a sibling poisons reused
register storage. The fixture alternates original/changed bodies, history verification,
persistent registers and scalar-call options. The callees contain Calls so ordinary
fallback remains necessary even with scalar calls enabled. Both expected failures
are evidence, not accepted correctness. No original project guest or timing run.

Then add exactly the derived boolean to each bound callee input, audit other
resumable emitter dependencies, qualify the full runtime and actual saved suites
before further optimization. Preserve failing artifacts. No new acceptance claim
or replay of earlier performance histories. Locks/resources and ownership match
existing runtime experiments:2workers, shared target never cleaned, dynamicbuild
floor max(14GiB,8GiB+2*allocated target),8GiB before children/closure. No peer work,
subagents, goal calls or service activation.

The two expected failures are now reproduced and closed: caller emission changes
while the old key stays equal; cached execution fails the new zero-register assertion
while fresh execution passes. Fix binds the exact current precomputed boolean and
bumps the internal key domain tov3. Other direct-callee emission inputs inspected:
call-slot argument sizes, frame/register/result layout, scalar eligibility/extent/
maximum and success steps/current target. Existing relocation/current-assertion and
code/entry budgets remain. This audit is not a formal completeness proof.

Qualification runs654workspace tests/profile+16ignored,33diagnostic integration
controls and a feature-off VM build. Reuse only the exact442Python+22skip record
after unchanged scripts/tests hashes.36sessions69clients reaped. Preserve standard
and diagnostic binaries separately. Replay16actual saved parser suites with every
hit freshly verified and all1,824original outcomes matched before diagnostic replay.
