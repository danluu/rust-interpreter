# Direct unchanged run-make continuation

This is source-only preparation. No compiler, recipe, metadata probe or synthetic
test has run for this packet. There is no plan, input freeze, launch, or claim
that future compiler outputs exist. The accepted source proposal is retained
unchanged in `PROPOSAL.md`; its 19 source bindings and the eight additional helper
bindings are exact current source bytes.

`prepare.py` requires the actual successful build02 terminal, all eight stages
and 25 exact child records, completed compiler/support inventories, full raw
streams, and an independently passed audit binding both terminal and compiled
JSON hashes. Failed build01 remains a separate retained result. The independent
audit's concrete field mapping must be confirmed against its actual schema
before a future freeze; it is not a prospective verification result.

The new controller creates a fresh `N/run-make-01`, compiles the unchanged recipe
once with D2 and actual support artifacts, then executes that new recipe once.
All nested compiler calls use E2. It preserves compiletest's actual dependency
directory iteration order, separate rlib/rmeta identity, stable recipe API
restriction, target and loader environment, and normal compiletest version
override. No wrapper, fixture edit, instrumentation or performance sample is
introduced. The fixture itself removes the version override for ordinary
histories and restores empty/nonempty values only for its existing controls.

Actual support discovery is deliberately fail-closed: it associates the sole
retained support rustc command and parent Cargo/shim route with D2, source,
target, extra filename, dep-info and completed artifact inventory. Separate
metadata directories are permitted only for the identical producer stem and
bytes. The actual future output format must satisfy this proof before launch;
missing or ambiguous provenance does not authorize another support build.

LLVM, C/C++, ar, rustdoc and sanitizer variables are explicitly omitted as unused.
The unchanged recipe calls Rustc, native run, filesystem and assertion helpers;
its executed helper path reads only the bound compiler, target, cwd and loader
variables. No LLVM component probe is needed. RUST_TEST_TMPDIR follows
`Config::tempdir` (the build-root `tmp` directory); threads are two and the doc
channel is the source-derived nightly URL for channel `dev`. This is not a claim
of complete compiletest environment identity for unused tool helpers.

`history.py` expands the unchanged source into 230 ordered verbose blocks:
144 compiler calls (105 successful and 39 expected failures) and 86 successful
native executions. It audits full command/env-change spelling, flags, status,
order and complete output slices; the real recipe must additionally pass all
its original diagnostic, tree/journal/poststate, corruption, invalidation and
version-override assertions. The fixed Debug-output grammar is conservative;
an unexpected producer spelling is retained as a failure, not silently ignored.
Nested PIDs and start times are unavailable in run-make-support's output and are
not claimed. All top-level process identities and complete raw output remain
in the ordinary owned-child receipts. These are qualification controls, not
edited-build benchmark timings.

The loader helper reads actual Mach-O bytes without extra commands. D2/E2
providers must already be admitted by the build; the generated recipe may load
only uniquely resolved files from the frozen D2/E2/support inventories. Distinct
possible routes reject conservatively. System dyld-cache libraries retain the
bound platform assumption, not a full file-hash claim. No global loader tracing
is enabled, because that would change nested diagnostic equality. Unproved new
loader behavior requires a separate reviewed metadata plan.

The copied budget helper changes only exact cwd/output routes, aggregate
evidence accounting and inheritance of the canonical descriptor. Canonical
admission remains 600 seconds; capacity stays 24/9/8 GiB, the complete N namespace
14 GiB, and aggregate failed build01/build02/run-make evidence 256 MiB. It can
signal only a freshly created, revalidated owned group on capacity failure.
Source, SDK, provider, support and compiler bytes are checked before and after.
The successful recipe must restore input.rs exactly to fixture.rs; all final
output membership and hashes are retained. Failure leaves partial evidence and
outputs intact, with no automatic retry or deletion.

Before launch: finish actual build02, review its independently verified output
schema and the actual support producer command, source-review these helpers,
then run the read-only preparer and review the resulting concrete plan/freeze.
The preparer fails on the currently missing prerequisite; it has not been run.

Producer discovery now parses the exact two bootstrap shims and every plausible
Cargo context in the successful support child's two retained streams. Every
context must yield the same complete effective environment. It binds D2 Cargo,
RUSTC_REAL/SNAPSHOT/libdirs, stage zero, wrapper and version settings, and rejects
unadmitted loader overrides. The bound tool.rs macro builds RunMakeSupport as
Mode::ToolBootstrap; cargo.rs selects the raw D2 sysroot and session.rs selects
bootstrap-tools output. Those paths deliberately differ from the compiler
producer's artificial stage0-sysroot and stage1-rustc directory. `producer.py`
adapts the reviewed composition02 parser (source SHA e36c61748bff582bba0f1c22cd5650cd7744b32a96409f7652963870f507b7c6)
without importing or changing that agent's files. Actual output discovery is
still unqualified until the compiler build succeeds.

Both preparer and execution guards preserve all build02 ancestor Cargo.toml
presence and absence assertions. The future independent audit must use X's
actual schema: status verified, 25 children, eight compiler stages, and exact
receipt_sha256/compiled_sha256. No synthetic passed report or future file is
created by this source preparation.
