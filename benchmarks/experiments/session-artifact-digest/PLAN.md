# Request-local artifact digest reuse

The corrected input-phase replay attributes about8.6ms to catalog validation;
source inspection finds a second SHA256 of the same29MB artifact already hashed
by server input binding. Test one immutable owned actual-byte digest shared by
those two checks. This observation is not an end-to-end savings estimate.

Experimental feature jit-artifact-digest-reuse composes the corrected v3 template
key and65,536-op size tier. Its byte owner has private bytes/digest fields, computes
its own SHA256 and exposes only shared views. No digest supplied by a requester,
catalog, file metadata, previous request or persisted cache can construct it.
Decode these exact held bytes, reject trailing bytes, check all catalog identities,
and run full Program validation before scheduling fresh private guest/native owners.
Strict compiler type/borrow checking, current limits and report reservation remain.
Feature-off ordinary catalog validation still hashes the supplied bytes itself.

Qualification: full debug/release workspace (656passed+16ignored per profile),
33diagnostic integration controls,10feature-off session controls, default VM build.
Reuse the closed442passed/22skipped Python record only after unchanged scripts/tests
bindings verify. Retain48owned server and92VM-client terminal records. New tests
cover changed same-size bytes, stale catalogs despite correct request digests,
header/entry identities, and original ownership; existing socket tests retain
malformed/trailing/partial/current-program rejection and recovery.

Next replay16saved actual parser suites (1,824test invocations), verifying every
cache hit independently and matching exact outcomes/failure text and kernel CPU.
A separate observer replay may check where cost moved; it cannot establish speedup.
Only a new changed-source primary with a freshly composed qualified installed tool
can establish benefit. Earlier failed/unmeasurable primaries remain closed; no
unchanged retry or adoption. Full multi-project/regression gates follow only if
that primary passes. Do not use the previous installed size-tier tool with old key.

Serialize using benchmark.lock, two workers, existing dedicated target only.
Build admission max(14GiB,8GiB+2*allocated target); replay12GiB, per-child8GiB.
No target cleaning, peer process control, subagents or goal changes. Source-bound
supervised one-shot runs and complete closures precede any source change.
