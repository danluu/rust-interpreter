# Future qualification; no executable launch is authorized here

The next build decision depends on the retained off/on Ruff profile. A broad
lowering profile does not separately measure option hashing, JSON work, or
replay verification. Any finer diagnostic spans need their own reviewed source
and measurement plan. This artifact makes no adoption or performance claim.

## Source and construction

1. Independently verify the patch, exact compiler base commit and retained
   SHA-256/Git blob identities. Require exactly the two stated code changes.
2. Derive a new acyclic body-cache `SOURCE_IDENTITY` using the inherited full
   qualified hook/gate/storage/verifier closure plus the full modified
   `compiler/rustc_middle/src/ty/context.rs`. Preserve the historical identity
   and manifests separately. Freeze the resulting three-file build patch,
   source tree, configuration, tool/provider closure and controller before
   any actual compiler build. Never relabel an old compiler qualification.
3. Use a fresh owned candidate build under the established canonical lock,
   recorded capacity limits, raw receipts and bounded supervision. The existing
   runtime/source/tool owners stay immutable. Exact commands and budgets are
   future review inputs, not implied by this document.

## Focused controls

`controls/driver.rs` is concrete **uncompiled/unrun** control source for the
candidate rustc-driver API. Its fixture is independent of Ruff and Oxc.
Compile it against the actual new compiler and driver under a reviewed plan,
binding executable, sysroot, loader and source identities. Run it once in
`serial` mode and once in `parallel` mode, in separate processes and fresh
owned output directories. Compiler options preserve identical source/output
paths across the eight contexts within each process.

- Repeated identical options must retain the same hash.
- Change a tracked option (`-Copt-level`), then return to the original state.
  Both incremental and crate hashes must change and restore. This rejects a
  stale process-global cache across compiler contexts.
- Change `TRACKED_NO_CRATE_HASH` lint options, then restore them. The
  incremental hash must change while the crate hash stays equal. This rejects
  accidentally caching the `true` variant or sharing an old context's value.
- Change untracked `self-profile-events` while profiling remains disabled.
  Both hashes must remain equal. No profile output is requested by this control.
- In the parallel process, every context uses `-Zthreads=2`. A barrier and
  `par_join` require two distinct compiler worker threads to call the accessor
  concurrently and repeatedly. The first pair starts before any accessor call
  in that context; HIR caching is disabled in these hash-only controls.
  Do not change rustc's process-global dynamic thread mode within one process.
- Every actual accessor result must equal the original uncached option hash
  for that context. The serial path performs the same repeated read checks.

The final record must contain exactly eight context observations and one
passing terminal per process. Retain all raw output and any failure; a source
review or patch-application check is not evidence these Rust controls passed.
The controller must bound and retain any unexpected parallel-control hang.

## Existing compiler behavior controls

Run the pinned `tests/run-make/hir-body-cache-capture` history unchanged with
the new compiler. It compares actual program behavior and exact raw JSON
diagnostics; exercises source restoration, span rebasing, trait/import changes,
tracked lint changes and active language features; introduces real uncalled
type, borrow, const-evaluation and unconditional-panic errors; corrupts cached
records and checks ordinary fallback; and checks that both empty and nonempty
`RUSTC_FORCE_RUSTC_VERSION` overrides reject body caching.

Preserve all existing journal/tree/current-context tests and always-on hit
recapture/poststate audits. Existing option-hash tests in
`compiler/rustc_interface/src/tests.rs` cover clone behavior, ordering, tracked,
untracked, and `TRACKED_NO_CRATE_HASH` distinctions. Reuse those controls;
do not replace them with a test of `OnceLock` alone.

## Performance decision

Only after source/compiler correctness qualification should a distinct
predeclared comparison bind ordinary runtime composition and representative
development workloads. Keep baseline/candidate cold and warm states separate,
perform real source edits and unchanged guest assertions, retain all outcomes,
and apply independent holdout validation before any broad adoption claim.
Actual native build-script/proc-macro work remains part of measured application
cost. No fixture or project-specific fast path is included in this candidate.
