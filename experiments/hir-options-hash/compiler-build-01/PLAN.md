# Candidate compiler stages, prepared but unrun

Owner: `/Users/danluu/dev/rust-interp-runtime-exporter-20260918` (X).
Candidate namespace: X/.work/hir-options-hash-compiler-01 (N).
Candidate source: N/source (S). Candidate build: S/build (B).
Candidate stage1: B/aarch64-apple-darwin/stage1 (E2).
Candidate stage0 beta: B/aarch64-apple-darwin/stage0 (D2).
Private Cargo home: N/cargo-home. Future auxiliary beta sysroot: N/beta-sysroot.

The source/provider acquisition is separately reviewed and approved conditional
on passing filesystem controls and actual 24 GiB admission. Its successful
terminal and acquired.json, exact new source commit, complete source contents,
backtrace, bootstrap, all copied seed/provider hashes and current identities
become required inputs of the build metadata stage. No compilation can execute
from a prospective acquisition path or a source-only patch receipt.

The next metadata-only controller must bind the current OS27 executors,
resolved Python/Git/clang/ld/xcrun routes, selected SDK and SDKSettings, source
and parent Cargo configurations, seed archive content and every compiler source
file. Loader dependencies are checked using the existing bounded Mach-O closure
reader and actual selected routes. Old September13 file/device identities are
historical evidence only. SDKSettings alone does not bind all SDK headers;
reuse the existing full SDK/provider guard. The actual bootstrap sources and
src/stage0 must establish the exact already-seeded LLVM cache key. An absent or
changed seed is a failure, not permission for a LLVM build or download.

Actual build/controller freeze follows metadata. It uses explicit current
provider paths, environment allowlisting, N/cargo-home, offline Cargo, two jobs,
no downloaded rustc, and the unchanged bootstrap configuration. It verifies the
full source and input closure before/after each stage. It records expanded
bootstrap commands so source remapping and the actual candidate commit in
CFG_VIRTUAL_RUST_SOURCE_BASE_DIR/CFG_VIRTUAL_RUSTC_DEV_SOURCE_BASE_DIR are proved.

The finite owned namespace cap is 14 GiB allocated by unique inode, including
source, provider extraction, build cache, future B3 and driver-control artifacts.
The new evidence namespace has a separate 256 MiB cap, reserved within the
24 GiB entry/9 GiB stop/8 GiB floor policy. A new owned command helper must
sample both free space and owned allocation while each child runs; a between-
command check alone is insufficient. Any capacity stop may control only its
fresh, fully revalidated process group using the existing owned-stage contract.
All raw output and failed attempts remain preserved.

The fixed initial compiler stages (cwd S) are:

```
./x check --stage 1 compiler/rustc_ast_lowering --jobs 2 -vv
./x test --stage 1 compiler/rustc_ast_lowering --jobs 2 -vv
./x build --stage 1 compiler/rustc library --jobs 2 -vv
E2/bin/rustc -vV
E2/bin/rustc --print sysroot
E2/bin/rustc -Zhelp
./x test --stage 1 compiler/rustc_interface --jobs 2 -vv
./x build --stage 1 src/tools/run-make-support --jobs 2 -vv
```

Identity probes must name the actual new source commit, E2 sysroot and unchanged
compiler policy flags. Lowering tests retain every one of the 27 existing
controls. The complete rustc_interface target retains all option-hash tests.
Raw test names/counts must be checked against source-derived expected sets;
zero exit alone is insufficient. No test filters skip existing corruption,
tree/journal/poststate, feature or diagnostics checks.

Run-make is a separately frozen continuation once these support outputs exist.
`run_rmake_test` has no compile-only branch, so the test is not run through
compiletest. Mirror exact source
src/tools/compiletest/src/runtest/run_make.rs for a single direct recipe build:

```
D2/bin/rustc -o N/native-controls/rmake \
  [each actual support build out directory as -Ldependency=...] \
  --extern run_make_support=ACTUAL_NEW_SUPPORT_RLIB \
  --edition=2024 S/tests/run-make/hir-body-cache-capture/rmake.rs \
  -Cprefer-dynamic [--extern run_make_support=ACTUAL_NEW_SUPPORT_RMETA] \
  -Dunused_must_use
```

Recipe compilation uses RUSTC_BOOTSTRAP=-1, as the exact compiletest source
requires. The resolved out-directory membership and rlib/rmeta/dynamic library
bytes are actual metadata inputs, never guessed filenames. Then execute the
new recipe **once**, with the unchanged fixture and exact derived run_make
environment, direct unabridged stdout/stderr files, actual E2 RUSTC and D2/support
loader dependencies. Preserve compiletest's required host/target/source/build
variables and version-override behavior. The existing fixture removes the
ordinary override itself and tests empty/nonempty rejection explicitly.

New B3 metadata composition, real zero-failure strip, beta/private/native role
qualification and the concrete serial/parallel hash driver form a later stage.
No old B2 metadata may substitute for the new candidate private metadata. Each
driver process runs all eight sequential contexts; only the parallel process
sets threads=2. Actual driver results must equal uncached false-option hashes
and preserve changed/restored tracked and TRACKED_NO_CRATE_HASH distinctions.

Only after those actual qualifications may new runtime installation/exporter
composition and application performance comparisons be proposed. Existing R,
shared std, adopted VM and published tools remain immutable throughout.
