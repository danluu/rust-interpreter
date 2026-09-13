# Empty-wrapper compiler-info cache qualification

Cargo's process builder ignores an explicit empty wrapper, while its compiler
fingerprint attempts to inspect that empty path and disables rustc-info caching.
The prototype filters empty normal/workspace wrapper paths at the fingerprint
boundary. It preserves the environment override that disables configured
wrappers and leaves real executable, compiler, rustup, argument and environment
fingerprinting unchanged. No cache-disable option is overridden.

This experiment uses the owned Cargo source revision
`3c0b534756e166d12eb9fd2e1abfe5b42ac6101e`. Cargo has prior optimization exposure
and is excluded from fresh holdouts. `cargo-info-cache.patch` contains the entire
production change and the three-case regression; `scripts/build_cargo.py` and its
separate executable-publication experiment are not used or changed.

The matched stock and candidate executables use the same owned source path,
pinned nightly-2026-09-08 compiler, Cargo default features, release optimization,
release debug level 1 and target directory. Incremental tool compilation is
disabled. Source inputs are frozen for each command. The test addition is shared
by both states and is not linked into the Cargo executable; the only production
source difference is `src/util/rustc.rs`. The shared `focused.rs` integration
entry includes the complete upstream `rustc_info_cache` module and its existing
Cargo invocation helper. It avoids compiling unrelated integration-test modules
while preserving all three cache tests and every Cargo command they execute.

`qualify.py` acquires the shared workload lock with a bounded wait before any
format, fetch, build or test command. Dependency setup uses an owned Cargo home;
build/test targets, installed executables and fixtures are also task-owned.
Every child is drained and waited for before source restoration, including
receipt-publication failures. The original candidate bytes are staged atomically
before temporarily restoring the stock implementation. No peer checkout/cache or
workload is changed.

The planned sequence is:

1. Check formatting and fetch locked dependencies for the host target.
2. Temporarily restore stock production code, build stock release Cargo, and
   retain its source/compiler/build identities. Run the entire
   `rustc_info_cache` test module: the new empty-wrapper regression must fail,
   while both existing tests must pass. Install the executable after this test
   build, so any dependency-feature unification is part of both matched tools.
3. Restore the candidate source, build candidate release Cargo with the same
   settings, and run all three module tests successfully. Retain separate
   fixture histories and exact stdout/stderr/process receipts for both states.
4. Verify source restoration and every installed binary/source manifest, and
   publish correctness/build evidence separately from performance evidence.

The new regression exercises empty normal, workspace and both wrapper overrides
against nonexistent configured wrappers. Each case requires initial cache
miss/update, a warm hit without miss/update, and continued misses when
`CARGO_CACHE_RUSTC_INFO=0`. Existing tests exercise ordinary reuse, changed
compiler paths/timestamps and replacement of real normal/workspace wrappers.

This sequence is correctness and matched-tool setup, not a benchmark or evidence
that the 0.5 s target passed. Any later performance claim must compare these
matched stock/candidate executables, preserve all required compilation/test work
and include ordinary source edits and controls. Comparing a locally built
candidate directly against the distributed Cargo binary would mix build-profile,
feature and source differences into the claimed optimization.

After coordinating a build window with the other workload owner:

```sh
python3 benchmarks/experiments/cargo-info-cache/qualify.py \
  --source .work/sources/cargo --run-id cargo-info-cache-build-01 \
  --lock-wait-seconds 45
```

For another independent checkout at the exact revision, apply the tracked patch
to that owned checkout first. The driver checks the full diff against the patch
and refuses unknown source edits. A failed run is retained under its run ID;
retries use a new run ID and retain any previous build caches as setup history.
