# Explicit per-arm runtime compiler proposal

This is an unapplied source proposal. No R script, installed provider, benchmark,
application fixture, test body or holdout has changed. No proposed module or
fixture has been imported or executed. `before/` contains exact R source bytes;
`proposed/` and `proposal.patch` contain the candidate change for review.

The existing `--runtime-compiler-key` and `--std-mir-key` path keeps its shared
selection, existing argument checks and saved `runtime_compiler`/`std_mir` fields.
With neither new arm option present, the pure selector returns `None` and leaves
that path to its original implementation.

The optional new route requires both `--baseline-runtime-compiler-key` and
`--candidate-runtime-compiler-key`, an existing batched comparison, and explicit
baseline/candidate tool keys. Shared and per-arm declarations cannot be mixed,
even if their values happen to agree. With `--std-mir`, both
`--baseline-std-mir-key` and `--candidate-std-mir-key` are required; without it,
neither is allowed. Standard-library readiness already binds the compiler, so
one shared std cannot silently stand in for both distinct runtime compilers.
Duplicate new CLI options and incomplete selections fail before provider access.
A/A selections must use identical runtime and std keys as well as the existing
identical tool/settings/jobs checks.

The ordinary runtime loader and tool validator remain authoritative. Each arm
validates its selected installed toolset against its actual loaded runtime.
The ordinary prepared-std reader checks the selected std against that runtime.
An identical runtime/std pair may share setup; both tool associations are still
checked. Each command receives its own runtime/std arguments, and the existing
`workflow_compiler.verify_runtime_call` checks the command and actual launch
receipt. All runtime/tool/std associations are revalidated at completion.

Only the new route adds `runtime_arms` and `std_mir_by_mode` report fields. The
former contains an exact selection and two explicit runtime receipts, prepared
std descriptors and tool keys. The saved verifier requires this shape, rejects
simultaneous shared/per-arm claims, and checks every call against its own arm.
It does not weaken bytecode equality, guest assertions, artifact checks or the
existing independently supplied compiler-flag comparison rules. A future
experiment that cannot satisfy these unchanged checks needs a separate decision;
this proposal grants no exception.

Source edits/order, cycles, sample count, jobs, native reference, VM flags,
instruction/allocation limits, canonical locking, resource admission, cache
isolation, restoration, capture/wait behavior, timers and CPU accounting are
unchanged. Preparation/provider setup remains outside measured calls. Existing
build-to-ready and run metrics keep their original boundaries; no diagnostic
span is promoted to end-to-end latency. Fresh candidate/baseline keys and a
reviewed benchmark protocol are still required before any actual workload.

The fixture suite covers legacy delegation, conflicting/incomplete CLI routes,
duplicate options, A/A restrictions, exact runtime/std/tool routing, provider
callback failure propagation, wrong runtime and std associations, malformed
receipt shapes, detached metadata, and routing to the unchanged call validator.
Its fake providers are in-memory objects using `/fixture` strings; those paths
are never opened. Actual provider and benchmark integration remains unexecuted.

`derive_proposal.py` records the literal source transformation against the pinned
baseline. It writes fresh proposal files only; it does not apply the patch to R.
The final source assessment separately records AST-only checks and current hashes.
