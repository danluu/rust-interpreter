# Compiler continuation after parent workspace rejection, prepared but unrun

Owner: `/Users/danluu/dev/rust-interp-runtime-exporter-20260918` (X).
Candidate namespace: X/.work/hir-options-hash-compiler-01 (N).
Candidate source: N/source (S). Candidate build: S/build (B).
Candidate stage1: B/aarch64-apple-darwin/stage1 (E2).
Candidate stage0 beta: B/aarch64-apple-darwin/stage0 (D2).
Private Cargo home: N/cargo-home. Future auxiliary beta sysroot: N/beta-sysroot.

Source/provider acquisition and metadata qualification have passed. The latter
combines the retained metadata03 parser failure after 48 probes with the
successful two-probe continuation. Its unchanged closure binds every source
file, current OS27 executor, resolved Python/Git/clang/ld/xcrun route, complete
SDK file/link/directory inventory, and exact source-derived offline seed key.

Build01 completed two Git guards, extracted the beta seeds, and stopped before
Rust compilation when bootstrap Cargo discovered X's enclosing workspace.
The failed terminal and all three raw child histories stay immutable. Source
S and candidate commit `4de35bdacef0e3cd18a66bc30b5459c19e09b118` are unchanged.
This continuation retains the extracted stage0. It binds the exact current
partial build-tree membership/bytes and rechecks every archive-bound stage0
provider before invoking the still-uncompleted first stage.

The sole configuration remedy is X's parent workspace exclusion changing from
two named generated projects to all `.work` descendants. The original parent
manifest snapshot and actual six-control Cargo qualification are retained;
the new ancestor manifest is an explicit immutable build input. Compiler and
application manifests, dependencies and code are unchanged. An absent or
changed offline provider remains a failure, with no download or LLVM rebuild.

Actual build/controller freeze follows metadata. It uses explicit current
provider paths, environment allowlisting, N/cargo-home, offline Cargo, two jobs,
no downloaded rustc, and the unchanged bootstrap configuration. It verifies the
full source and input closure before/after each stage. It records expanded
bootstrap commands so source remapping and the actual candidate commit in
CFG_VIRTUAL_RUST_SOURCE_BASE_DIR/CFG_VIRTUAL_RUSTC_DEV_SOURCE_BASE_DIR are proved.

The finite owned namespace cap is 14 GiB allocated by unique inode, including
source, provider extraction, build cache, future B3 and driver-control artifacts.
The new `.work/hir-options-hash-compiler-build-02` evidence namespace has a
separate 256 MiB cap, reserved within the
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
