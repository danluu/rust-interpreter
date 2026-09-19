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
